from commander.connections import owner_lock
from commander.db import json
from commander.errors import DomainError
from commander.skills import definition


def owned_run(db, owner, run_id):
    row = db.one("SELECT * FROM runs WHERE id=%s AND owner_id=%s", (run_id, owner))
    if not row:
        raise DomainError("Run not found", 404)
    return row


def event(db, run_id, kind, payload=None):
    db.one(
        "INSERT INTO events(run_id,kind,payload) VALUES (%s,%s,%s) RETURNING id",
        (run_id, kind, json(payload or {})),
    )


def enqueue(db, settings, owner, data):
    with db.connect() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 720))", (str(owner),))
        count = conn.execute(
            "SELECT count(*) AS n FROM runs WHERE owner_id=%s AND created_at>now()-interval '1 day'",
            (owner,),
        ).fetchone()["n"]
        if count >= settings.max_daily_runs:
            raise DomainError("Daily run budget reached", 429, "budget_exceeded")
        conversation = data.conversation_id
        if (
            conversation
            and not conn.execute(
                "SELECT 1 FROM conversations WHERE id=%s AND owner_id=%s", (conversation, owner)
            ).fetchone()
        ):
            raise DomainError("Conversation not found", 404)
        if not conversation:
            conversation = conn.execute(
                "INSERT INTO conversations(owner_id,title) VALUES (%s,%s) RETURNING id",
                (owner, data.prompt[:100]),
            ).fetchone()["id"]
        conn.execute(
            "INSERT INTO messages(owner_id,conversation_id,role,content) VALUES (%s,%s,'user',%s)",
            (owner, conversation, data.prompt),
        )
        row = conn.execute(
            "INSERT INTO runs(owner_id,conversation_id,skill,skill_version,prompt) VALUES (%s,%s,%s,%s,%s) RETURNING *",
            (owner, conversation, data.skill, definition(data.skill)["hash"], data.prompt),
        ).fetchone()
    event(db, row["id"], "queued")
    return row


def detail(db, owner, run_id):
    row = owned_run(db, owner, run_id)
    return {
        **row,
        "events": db.all("SELECT * FROM events WHERE run_id=%s ORDER BY id", (run_id,)),
        "actions": db.all("SELECT * FROM actions WHERE run_id=%s ORDER BY created_at", (run_id,)),
        "evidence": db.all("SELECT * FROM evidence WHERE run_id=%s ORDER BY fetched_at", (run_id,)),
    }


def cancel(db, owner, run_id):
    with owner_lock(db, owner):
        row = owned_run(db, owner, run_id)
        if row["status"] not in ("succeeded", "failed", "cancelled"):
            db.one(
                "UPDATE runs SET status='cancelled',updated_at=now() WHERE id=%s RETURNING id",
                (run_id,),
            )
            db.one(
                "UPDATE actions SET status='denied',error='Run cancelled' WHERE run_id=%s AND status IN ('pending','approved') RETURNING id",
                (run_id,),
            )
            event(
                db,
                run_id,
                "cancelled",
                {"message": "Further actions stopped. Completed effects are not undone."},
            )
    return detail(db, owner, run_id)
