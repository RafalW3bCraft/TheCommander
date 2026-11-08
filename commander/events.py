"""Bounded, resumable run events; HTTP status reads remain the recovery authority."""

import asyncio
import json
from time import monotonic
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from commander import auth
from commander.errors import DomainError

MAX_CURSOR = 2**63 - 1
MAX_STREAM_SECONDS = 25
POLL_SECONDS = 1
HEARTBEAT_SECONDS = 10
BATCH_SIZE = 100
TERMINAL = {"succeeded", "failed", "cancelled"}


def frame(kind, payload, event_id=None):
    # Event names are application constants; all user-controlled text is JSON escaped.
    prefix = f"id: {event_id}\n" if event_id is not None else ""
    return f"{prefix}event: {kind}\ndata: {json.dumps(jsonable_encoder(payload), separators=(',', ':'))}\n\n"


def owned_status(db, owner, run_id):
    row = db.one("SELECT status FROM runs WHERE id=%s AND owner_id=%s", (run_id, owner))
    if not row:
        raise DomainError("Run not found", 404)
    return row["status"]


def snapshot(db, request, owner, run_id, after):
    # Reauthenticate without principal's per-request throttle: each poll is not a request.
    session = auth.authenticate(db, request)
    if session["owner_id"] != owner:
        raise DomainError("Sign in to continue", 401, "unauthenticated")
    status = owned_status(db, owner, run_id)
    rows = db.all(
        """SELECT e.id,e.run_id,e.kind,e.payload,e.created_at FROM events e
        JOIN runs r ON r.id=e.run_id WHERE r.id=%s AND r.owner_id=%s AND e.id>%s
        ORDER BY e.id LIMIT %s""",
        (run_id, owner, after, BATCH_SIZE),
    )
    return status, rows


async def run_stream(db, request, owner, run_id, after):
    deadline = monotonic() + MAX_STREAM_SECONDS
    heartbeat_at = monotonic() + HEARTBEAT_SECONDS
    previous_status = None
    while not await request.is_disconnected():
        if monotonic() >= deadline:
            yield frame("end", {"reason": "reconnect"})
            return
        try:
            status, rows = await run_in_threadpool(snapshot, db, request, owner, run_id, after)
        except DomainError as exc:
            if exc.status == 401:
                yield frame("session_expired", {"code": "unauthenticated"})
            else:
                yield frame("access_lost", {"code": "not_found"})
            return
        if status != previous_status:
            yield frame("status", {"run_id": str(run_id), "status": status})
            previous_status = status
        for row in rows:
            if await request.is_disconnected():
                return
            after = row["id"]
            # bigint IDs stay strings on this boundary to avoid JS precision loss.
            yield frame("run_event", {**row, "id": str(after)}, after)
        if len(rows) == BATCH_SIZE:
            continue
        if status in TERMINAL:
            yield frame("end", {"reason": "terminal"})
            return
        if monotonic() >= heartbeat_at:
            yield ": heartbeat\n\n"
            heartbeat_at = monotonic() + HEARTBEAT_SECONDS
        # Queries above release their connections; no transaction survives this wait.
        await asyncio.sleep(POLL_SECONDS)


def install_event_routes(app, db, principal):
    @app.get(
        "/api/runs/{run_id}/events",
        response_class=StreamingResponse,
        responses={
            200: {
                "description": (
                    "SSE: run_event JSON has id (decimal string), run_id, kind, payload, "
                    "created_at. status has run_id/status. end has reason terminal or reconnect. "
                    "session_expired and access_lost have code. Only run_event advances the "
                    "cursor. Comments are heartbeats. Streams close after 25 seconds; resume "
                    "with Last-Event-ID (takes precedence over after). Refresh run detail for "
                    "results/actions; events are progress notifications, not token streaming."
                ),
                "content": {"text/event-stream": {"schema": {"type": "string"}}},
            },
            401: {"description": "Session missing or expired"},
            404: {"description": "Run missing or inaccessible"},
        },
    )
    def run_events(
        run_id: UUID,
        request: Request,
        after: Annotated[int, Query(ge=0, le=MAX_CURSOR)] = 0,
        last_event_id: Annotated[int | None, Header(ge=0, le=MAX_CURSOR)] = None,
        owner=Depends(principal),
    ):
        owned_status(db, owner, run_id)
        cursor = after if last_event_id is None else last_event_id
        return StreamingResponse(
            run_stream(db, request, owner, run_id, cursor),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )
