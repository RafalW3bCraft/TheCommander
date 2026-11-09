"""Authenticated project scope and durable approval/state transitions."""

from uuid import UUID

from commander import auth, demo_grants, preferences
from commander.db import json
from commander.errors import DomainError
from commander.sandbox.contracts import Decision, TaskInput, browser_policy, domain_name, safe_url

COLUMNS = "id,project_id,kind,goal,url,status,approval_digest,approval_expires_at,error,created_at,updated_at"


def get(db, owner, job_id):
    row = db.one("SELECT * FROM sandbox_jobs WHERE id=%s AND owner_id=%s", (job_id, owner))
    if not row:
        raise DomainError("Sandbox task not found", 404)
    return row


def create(db, settings, owner, data):
    auth.require_active(db, owner)
    if not settings.sandbox_enabled:
        raise DomainError(
            "Sandbox execution is disabled by the operator", 409, "capability_unavailable"
        )
    if not db.one(
        "SELECT 1 FROM sandbox_heartbeats WHERE id='runner' AND seen_at>now()-interval '30 seconds'"
    ):
        raise DomainError(
            "Sandbox runner is offline; contact the operator", 503, "worker_unavailable"
        )
    if not settings.sandbox_model or (data.kind == "browser" and not settings.sandbox_vision_model):
        raise DomainError(
            "Configure Vultr text and browser vision models first", 409, "unavailable_model"
        )
    if not db.one("SELECT id FROM projects WHERE id=%s AND owner_id=%s", (data.project_id, owner)):
        raise DomainError("Project not found", 404)
    if data.kind == "browser":
        try:
            domains = [domain_name(d) for d in settings.sandbox_browser_domains]
        except ValueError:
            raise DomainError(
                "Operator browser domain policy is invalid", 503, "destination_denied"
            ) from None
        safe_url(data.url, domains)
        browser_policy(settings, data.url)
    effective = preferences.resolve(db, settings, owner)
    # Serialize admission to enforce daily and concurrent bounds under races.
    with db.connect() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(714896)")
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 720))", (str(owner),))
        if (
            conn.execute(
                "SELECT count(*) AS n FROM sandbox_jobs WHERE status IN ('queued','running','approved','waiting_approval')"
            ).fetchone()["n"]
            >= 20
        ):
            raise DomainError("Sandbox queue is full; try again later", 429, "queue_full")
        demo_grants.check_admission(db, owner, conn=conn)
        counts = conn.execute(
            """SELECT count(*) FILTER (WHERE created_at>now()-interval '1 day') AS daily,
         count(*) FILTER (WHERE status IN ('queued','running','approved','waiting_approval')) AS active
         FROM sandbox_jobs WHERE owner_id=%s""",
            (owner,),
        ).fetchone()
        if (
            counts["daily"]
            + conn.execute(
                "SELECT count(*) AS n FROM runs WHERE owner_id=%s AND created_at>now()-interval '1 day'",
                (owner,),
            ).fetchone()["n"]
            >= effective.max_daily_runs
            or counts["active"] >= 5
        ):
            raise DomainError("Sandbox admission limit reached", 429, "budget_exceeded")
        return conn.execute(
            """INSERT INTO sandbox_jobs(owner_id,project_id,kind,goal,url)
          VALUES (%s,%s,%s,%s,%s) RETURNING *""",
            (owner, data.project_id, data.kind, data.goal, data.url),
        ).fetchone()


def decide(db, owner, job_id, data):
    auth.require_active(db, owner)
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM sandbox_jobs WHERE id=%s AND owner_id=%s FOR UPDATE", (job_id, owner)
        ).fetchone()
        if not row:
            raise DomainError("Sandbox task not found", 404)
        row = conn.execute(
            """UPDATE sandbox_jobs SET status=%s,approved_at=CASE WHEN %s THEN now() ELSE NULL END,
           events=events || %s,updated_at=now() WHERE id=%s AND owner_id=%s
           AND status='waiting_approval' AND approval_digest=%s AND approval_expires_at>now() RETURNING *""",
            (
                "approved" if data.approve else "denied",
                data.approve,
                json([{"kind": "human_approved" if data.approve else "human_denied"}]),
                job_id,
                owner,
                data.digest,
            ),
        ).fetchone()
        if not row:
            raise DomainError(
                "Approval expired or task changed; reload and inspect", 409, "approval_conflict"
            )
        return row


def cancel(db, owner, job_id):
    row = get(db, owner, job_id)
    # Running browser effects cannot be undone. The worker kills on its next poll.
    if row["status"] in ("queued", "running", "waiting_approval", "approved"):
        return db.one(
            """UPDATE sandbox_jobs SET status=CASE WHEN status='running' AND approved_at IS NOT NULL
          THEN 'uncertain' ELSE 'cancelled' END,updated_at=now(),events=events || %s
          WHERE id=%s AND owner_id=%s AND status IN ('queued','running','waiting_approval','approved') RETURNING *""",
            (json([{"kind": "cancel_requested"}]), job_id, owner),
        ) or get(db, owner, job_id)
    return row


def install(app, db, settings, principal):
    from fastapi import Depends, Request

    @app.get("/api/sandbox/status")
    def status(owner=Depends(principal)):
        row = db.one("SELECT seen_at FROM sandbox_heartbeats WHERE id='runner'")
        online = db.one(
            "SELECT 1 FROM sandbox_heartbeats WHERE id='runner' AND seen_at>now()-interval '30 seconds'"
        )
        return {
            "enabled": settings.sandbox_enabled,
            "worker_online": bool(online),
            "worker_seen_at": row["seen_at"] if row else None,
            "provider": "vultr",
            "model": settings.sandbox_model,
            "vision_model": settings.sandbox_vision_model,
            "domains": settings.sandbox_browser_domains,
            "runtime": settings.sandbox_runtime,
        }

    @app.get("/api/sandbox/jobs")
    def jobs(project_id: UUID | None = None, owner=Depends(principal)):
        return db.all(
            "SELECT "
            + COLUMNS
            + " FROM sandbox_jobs WHERE owner_id=%s AND (%s::uuid IS NULL OR project_id=%s) ORDER BY created_at DESC LIMIT 50",
            (owner, project_id, project_id),
        )

    @app.post("/api/sandbox/jobs", status_code=201)
    def new(data: TaskInput, owner=Depends(principal)):
        return create(db, settings, owner, data)

    @app.get("/api/sandbox/jobs/{job_id}")
    def detail(job_id: UUID, owner=Depends(principal)):
        return get(db, owner, job_id)

    @app.get("/api/sandbox/jobs/{job_id}/artifacts")
    def artifacts(job_id: UUID, owner=Depends(principal)):
        get(db, owner, job_id)
        rows = db.all(
            "SELECT id,name,media_type,octet_length(data) AS size_bytes,sha256 FROM sandbox_artifacts WHERE job_id=%s AND owner_id=%s AND deleted_at IS NULL ORDER BY created_at",
            (job_id, owner),
        )
        return [
            {**row, "download_url": f"/api/sandbox/jobs/{job_id}/artifacts/{row['id']}"}
            for row in rows
        ]

    @app.get("/api/sandbox/jobs/{job_id}/artifacts/{artifact_id}")
    def download(job_id: UUID, artifact_id: UUID, owner=Depends(principal)):
        from fastapi import Response

        get(db, owner, job_id)
        row = db.one(
            "SELECT name,media_type,data FROM sandbox_artifacts WHERE id=%s AND job_id=%s AND owner_id=%s AND deleted_at IS NULL",
            (artifact_id, job_id, owner),
        )
        if not row:
            raise DomainError("Artifact not found", 404)
        return Response(
            bytes(row["data"]),
            media_type=row["media_type"],
            headers={
                "Content-Disposition": f'attachment; filename="{row["name"]}"',
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store",
            },
        )

    @app.delete("/api/sandbox/jobs/{job_id}/artifacts/{artifact_id}")
    def delete_artifact(job_id: UUID, artifact_id: UUID, owner=Depends(principal)):
        get(db, owner, job_id)
        row = db.one(
            "UPDATE sandbox_artifacts SET data=NULL,deleted_at=now() WHERE id=%s AND job_id=%s AND owner_id=%s AND deleted_at IS NULL RETURNING id",
            (artifact_id, job_id, owner),
        )
        if not row:
            raise DomainError("Artifact not found", 404)
        db.one(
            "UPDATE sandbox_jobs SET events=events || %s WHERE id=%s AND owner_id=%s RETURNING id",
            (json([{"kind": "artifact_deleted", "artifact_id": str(artifact_id)}]), job_id, owner),
        )
        return {"status": "deleted"}

    @app.delete("/api/sandbox/jobs/{job_id}/evidence")
    def delete_evidence(job_id: UUID, owner=Depends(principal)):
        row = get(db, owner, job_id)
        if row["status"] in {"queued", "running", "approved", "waiting_approval"}:
            raise DomainError("Cancel the task before deleting its evidence", 409, "task_active")
        db.one(
            "UPDATE sandbox_jobs SET evidence='{}',approval_snapshot=approval_snapshot-'screenshot',events=events || %s WHERE id=%s AND owner_id=%s RETURNING id",
            (json([{"kind": "evidence_deleted"}]), job_id, owner),
        )
        return {"status": "deleted"}

    @app.get("/api/sandbox/jobs/{job_id}/calls")
    def calls(job_id: UUID, owner=Depends(principal)):
        get(db, owner, job_id)
        return db.all(
            "SELECT id,phase,provider,model,status,input_tokens,output_tokens,duration_ms,created_at FROM sandbox_calls WHERE job_id=%s AND owner_id=%s AND deleted_at IS NULL ORDER BY created_at",
            (job_id, owner),
        )

    @app.post("/api/sandbox/jobs/{job_id}/decision")
    def decision(job_id: UUID, data: Decision, request: Request, owner=Depends(principal)):
        if data.approve:
            auth.require_recent(db, owner, request.cookies.get("commander_session", ""))
        return decide(db, owner, job_id, data)

    @app.post("/api/sandbox/jobs/{job_id}/cancel")
    def cancellation(job_id: UUID, owner=Depends(principal)):
        return cancel(db, owner, job_id)
