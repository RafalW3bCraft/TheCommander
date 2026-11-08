"""Resumption, bounded streaming and session/owner isolation against PostgreSQL."""

import asyncio
import json
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from commander import auth, events
from commander.db import Database
from commander.db import json as db_json
from commander.errors import DomainError


@pytest.fixture
def event_app(settings):
    db = Database(settings)
    db.migrate()
    owner = db.one(
        "INSERT INTO owners(username,password_hash) VALUES ('events-owner','unused') RETURNING id"
    )["id"]
    token, _ = auth.session(db, {"id": owner, "username": "events-owner"})
    run = db.one(
        "INSERT INTO runs(owner_id,skill,skill_version,prompt) VALUES (%s,'conversation','test','fictional') RETURNING id",
        (owner,),
    )["id"]
    app = FastAPI()

    def principal(request: Request):
        return auth.authenticate(db, request)["owner_id"]

    @app.exception_handler(DomainError)
    async def error(request, exc):
        return JSONResponse({"code": exc.code}, status_code=exc.status)

    events.install_event_routes(app, db, principal)
    with TestClient(app) as client:
        client.cookies.set("commander_session", token)
        yield client, db, owner, run, token


def add_event(db, run, kind="progress", payload=None):
    return db.one(
        "INSERT INTO events(run_id,kind,payload) VALUES (%s,%s,%s) RETURNING id",
        (run, kind, db_json(payload or {})),
    )["id"]


def decoded(response):
    return [
        (
            next(line[7:] for line in chunk.splitlines() if line.startswith("event: ")),
            json.loads(next(line[6:] for line in chunk.splitlines() if line.startswith("data: "))),
        )
        for chunk in response.text.split("\n\n")
        if "event: " in chunk
    ]


def test_replays_only_new_owner_events_and_documents_sse(event_app):
    client, db, owner, run, _ = event_app
    first = add_event(db, run)
    second = add_event(db, run, payload={"message": "first\nline"})
    db.one("UPDATE runs SET status='succeeded' WHERE id=%s RETURNING id", (run,))
    response = client.get(f"/api/runs/{run}/events?after={first}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-store"
    frames = decoded(response)
    assert [payload["id"] for kind, payload in frames if kind == "run_event"] == [str(second)]
    assert frames[-1] == ("end", {"reason": "terminal"})
    assert (
        "text/event-stream"
        in client.get("/openapi.json").json()["paths"]["/api/runs/{run_id}/events"]["get"][
            "responses"
        ]["200"]["content"]
    )
    resumed = client.get(f"/api/runs/{run}/events?after=0", headers={"Last-Event-ID": str(second)})
    assert all(kind != "run_event" for kind, _ in decoded(resumed))


@pytest.mark.parametrize(
    "suffix,headers",
    [
        ("?after=-1", {}),
        ("?after=9223372036854775808", {}),
        ("", {"Last-Event-ID": "not-an-id"}),
        ("", {"Last-Event-ID": "-1"}),
        ("", {"Last-Event-ID": "9223372036854775808"}),
    ],
)
def test_invalid_cursors_rejected_before_stream(event_app, suffix, headers):
    client, _, _, run, _ = event_app
    assert client.get(f"/api/runs/{run}/events{suffix}", headers=headers).status_code == 422


def test_session_and_run_ownership_required(event_app):
    client, db, _, run, _ = event_app
    other = db.one(
        "INSERT INTO owners(username,password_hash) VALUES ('other','unused') RETURNING id"
    )["id"]
    secret_run = db.one(
        "INSERT INTO runs(owner_id,skill,skill_version,prompt) VALUES (%s,'conversation','test','secret') RETURNING id",
        (other,),
    )["id"]
    assert client.get(f"/api/runs/{secret_run}/events").status_code == 404
    assert client.get(f"/api/runs/{uuid4()}/events").status_code == 404
    client.cookies.clear()
    assert client.get(f"/api/runs/{run}/events").status_code == 401


class StreamRequest:
    method = "GET"
    headers: dict[str, str] = {}

    def __init__(self, token):
        self.cookies = {"commander_session": token}
        self.disconnected = False

    async def is_disconnected(self):
        return self.disconnected


def test_session_revoked_during_stream_prevents_later_events(event_app, monkeypatch):
    _, db, owner, run, token = event_app
    monkeypatch.setattr(events, "POLL_SECONDS", 0)

    async def exercise():
        stream = events.run_stream(db, StreamRequest(token), owner, run, 0)
        assert "event: status" in await anext(stream)
        db.one(
            "DELETE FROM auth_sessions WHERE token_hash=%s RETURNING owner_id",
            (auth.digest(token),),
        )
        add_event(db, run, payload={"message": "must never arrive"})
        remaining = "".join([item async for item in stream])
        assert "event: session_expired" in remaining
        assert "must never arrive" not in remaining

    asyncio.run(exercise())


def test_disconnect_and_time_bound_close_stream(event_app, monkeypatch):
    _, db, owner, run, token = event_app
    monkeypatch.setattr(events, "MAX_STREAM_SECONDS", 0)

    async def exercise():
        request = StreamRequest(token)
        frames = [item async for item in events.run_stream(db, request, owner, run, 0)]
        assert len(frames) == 1 and '"reconnect"' in frames[0]
        request.disconnected = True
        assert [item async for item in events.run_stream(db, request, owner, run, 0)] == []

    asyncio.run(exercise())


def test_backlog_drains_in_order_and_current_status_is_recoverable(event_app, monkeypatch):
    client, db, _, run, _ = event_app
    monkeypatch.setattr(events, "BATCH_SIZE", 2)
    ids = [add_event(db, run) for _ in range(5)]
    db.one("UPDATE runs SET status='cancelled' WHERE id=%s RETURNING id", (run,))
    frames = decoded(client.get(f"/api/runs/{run}/events"))
    assert [payload["id"] for kind, payload in frames if kind == "run_event"] == list(map(str, ids))
    assert frames[0] == ("status", {"run_id": str(run), "status": "cancelled"})
    assert frames[-1] == ("end", {"reason": "terminal"})


def test_live_events_heartbeat_and_expiry(event_app, monkeypatch):
    _, db, owner, run, token = event_app
    monkeypatch.setattr(events, "POLL_SECONDS", 0)
    monkeypatch.setattr(events, "HEARTBEAT_SECONDS", 0)

    async def exercise():
        stream = events.run_stream(db, StreamRequest(token), owner, run, 0)
        assert "event: status" in await anext(stream)
        assert await anext(stream) == ": heartbeat\n\n"
        event_id = add_event(db, run, payload={"message": "arrived after connect"})
        live = await anext(stream)
        assert f"id: {event_id}\n" in live
        assert "arrived after connect" in live
        # Finish the current batch then invalidate the session before the next query.
        assert await anext(stream) == ": heartbeat\n\n"
        db.one(
            "UPDATE auth_sessions SET expires_at=now()-interval '1 second' WHERE token_hash=%s RETURNING owner_id",
            (auth.digest(token),),
        )
        assert "event: session_expired" in await anext(stream)
        assert [item async for item in stream] == []

    asyncio.run(exercise())


def test_deleted_run_and_disconnected_stream_stop_without_data(event_app, monkeypatch):
    _, db, owner, run, token = event_app
    monkeypatch.setattr(events, "POLL_SECONDS", 0)

    async def exercise():
        request = StreamRequest(token)
        stream = events.run_stream(db, request, owner, run, 0)
        assert "event: status" in await anext(stream)
        db.one("DELETE FROM runs WHERE id=%s RETURNING id", (run,))
        assert "event: access_lost" in await anext(stream)
        assert [item async for item in stream] == []
        request.disconnected = True
        assert [item async for item in events.run_stream(db, request, owner, run, 0)] == []

    asyncio.run(exercise())
