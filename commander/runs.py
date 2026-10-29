from commander.connections import Connections, owner_lock
from commander.db import json
from commander.errors import DomainError
from commander.skills import SkillInput, definition


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
    from commander import modes, projects
    from commander.preferences import resolve, values

    modes.validate(data.mode, data.skill)
    SkillInput(prompt=data.prompt)
    settings = resolve(db, settings, owner)
    with db.connect() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 720))", (str(owner),))
        count = conn.execute(
            "SELECT count(*) AS n FROM runs WHERE owner_id=%s AND created_at>now()-interval '1 day'",
            (owner,),
        ).fetchone()["n"]
        if count >= settings.max_daily_runs:
            raise DomainError("Daily run budget reached", 429, "budget_exceeded")
        conversation = data.conversation_id
        existing = None
        if conversation:
            existing = conn.execute(
                "SELECT * FROM conversations WHERE id=%s AND owner_id=%s FOR UPDATE",
                (conversation, owner),
            ).fetchone()
            if not existing:
                raise DomainError("Conversation not found", 404)
        project = projects.owned(
            conn, owner, data.project_id or (existing["project_id"] if existing else None)
        )
        if existing and existing["project_id"] != project["id"]:
            raise DomainError(
                "Conversation belongs to a different project", 409, "project_conflict"
            )
        if not conversation:
            conversation = conn.execute(
                "INSERT INTO conversations(owner_id,title,project_id) VALUES (%s,%s,%s) RETURNING id",
                (owner, data.prompt[:100], project["id"]),
            ).fetchone()["id"]
        row = conn.execute(
            "INSERT INTO runs(owner_id,conversation_id,skill,skill_version,prompt,settings_snapshot,project_id,mode) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *",
            (
                owner,
                conversation,
                data.skill,
                definition(data.skill)["hash"],
                data.prompt,
                json(values(settings)),
                project["id"],
                data.mode,
            ),
        ).fetchone()
        conn.execute(
            "INSERT INTO messages(owner_id,conversation_id,run_id,role,content) VALUES (%s,%s,%s,'user',%s)",
            (owner, conversation, row["id"], data.prompt),
        )
        conn.execute("INSERT INTO events(run_id,kind) VALUES (%s,'queued')", (row["id"],))
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
            with db.connect() as conn:
                conn.execute(
                    "UPDATE runs SET status='cancelled',lease_until=NULL,updated_at=now() WHERE id=%s",
                    (run_id,),
                )
                conn.execute(
                    "UPDATE actions SET status='denied',error='Run cancelled' WHERE run_id=%s AND status IN ('pending','approved')",
                    (run_id,),
                )
                conn.execute(
                    "INSERT INTO events(run_id,kind,payload) VALUES (%s,'cancelled',%s)",
                    (
                        run_id,
                        json(
                            {
                                "message": "Further actions stopped. Completed effects are not undone."
                            }
                        ),
                    ),
                )
    return detail(db, owner, run_id)


def reconcile_notes(db, settings, owner, run_id):
    import hashlib

    from commander.workspace import Workspace

    with owner_lock(db, owner):
        run = owned_run(db, owner, run_id)
        if run["status"] not in ("uncertain", "cancelled"):
            raise DomainError("Only uncertain or cancelled note effects can be reconciled", 409)
        Connections(db, settings).get(owner, "workspace")
        if db.one("SELECT 1 FROM actions WHERE run_id=%s", (run_id,)):
            raise DomainError("Use the external action receipt check", 409)
        intents = db.all(
            "SELECT payload FROM events WHERE run_id=%s AND kind='note_intent' ORDER BY id",
            (run_id,),
        )
        if not intents:
            raise DomainError("No note intent is available to reconcile", 409)
        recovered = []
        for item in intents:
            intent = item["payload"]
            try:
                content = Workspace(settings.workspace_root, owner).read(intent["name"])
            except DomainError:
                raise DomainError(
                    "The intended note is missing; run remains uncertain. No write retried.", 409
                ) from None
            if hashlib.sha256(content.encode()).hexdigest() != intent.get("sha256"):
                raise DomainError(
                    "The note content does not match its intent; run remains uncertain.", 409
                )
            recovered.append({"name": intent["name"], "sha256": intent["sha256"], "verified": True})
        with db.connect() as conn:
            conn.execute(
                "UPDATE runs SET status=CASE WHEN status='cancelled' THEN status ELSE 'succeeded' END,result=%s,error=NULL,updated_at=now() WHERE id=%s",
                ("Recovered verified notes: " + ", ".join(n["name"] for n in recovered), run_id),
            )
            conn.execute(
                "INSERT INTO events(run_id,kind,payload) VALUES (%s,'note_reconciliation',%s)",
                (run_id, json({"receipts": recovered})),
            )
    return detail(db, owner, run_id)
