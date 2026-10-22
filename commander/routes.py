from uuid import UUID

from fastapi import Depends

from commander import runs, schedules
from commander.broker import Broker
from commander.connections import Connections
from commander.contracts import (
    ActionView,
    Approval,
    ConnectionInput,
    ConnectionView,
    ConversationView,
    Issue,
    MessageView,
    Note,
    RunDetailView,
    RunInput,
    RunView,
    ScheduleEdit,
    ScheduleInput,
    ScheduleView,
    SkillView,
)
from commander.errors import DomainError
from commander.skills import DEFINITIONS
from commander.workspace import Workspace


def install_routes(app, db, settings, principal, transport):
    connections = Connections(db, settings, transport)
    broker = Broker(db, settings, transport)

    @app.get("/api/connections", response_model=list[ConnectionView])
    def list_connections(owner=Depends(principal)):
        return connections.list(owner)

    @app.post("/api/connections/import-environment")
    def import_environment(owner=Depends(principal)):
        return connections.import_environment(owner)

    @app.put("/api/connections/{kind}", response_model=list[ConnectionView])
    def save_connection(kind: str, data: ConnectionInput, owner=Depends(principal)):
        return connections.save(owner, kind, data)

    @app.post("/api/connections/{kind}/validate", response_model=list[ConnectionView])
    def validate_connection(kind: str, owner=Depends(principal)):
        return connections.validate(owner, kind)

    @app.delete("/api/connections/{kind}", response_model=list[ConnectionView])
    def revoke_connection(kind: str, owner=Depends(principal)):
        return connections.revoke(owner, kind)

    @app.get("/api/skills", response_model=list[SkillView])
    def skills(owner=Depends(principal)):
        return DEFINITIONS

    @app.get("/api/runs", response_model=list[RunView])
    def list_runs(owner=Depends(principal)):
        return db.all(
            "SELECT * FROM runs WHERE owner_id=%s ORDER BY created_at DESC LIMIT 100", (owner,)
        )

    @app.post("/api/runs", response_model=RunView)
    def create_run(data: RunInput, owner=Depends(principal)):
        return runs.enqueue(db, settings, owner, data)

    @app.get("/api/runs/{run_id}", response_model=RunDetailView)
    def run_detail(run_id: UUID, owner=Depends(principal)):
        return runs.detail(db, owner, run_id)

    @app.post("/api/runs/{run_id}/cancel", response_model=RunDetailView)
    def cancel_run(run_id: UUID, owner=Depends(principal)):
        return runs.cancel(db, owner, run_id)

    @app.get("/api/conversations", response_model=list[ConversationView])
    def conversations(owner=Depends(principal)):
        return db.all(
            "SELECT * FROM conversations WHERE owner_id=%s ORDER BY created_at DESC LIMIT 100",
            (owner,),
        )

    @app.get("/api/conversations/{conversation_id}/messages", response_model=list[MessageView])
    def messages(conversation_id: UUID, owner=Depends(principal)):
        if not db.one(
            "SELECT 1 FROM conversations WHERE id=%s AND owner_id=%s", (conversation_id, owner)
        ):
            raise DomainError("Conversation not found", 404)
        return db.all(
            "SELECT * FROM messages WHERE conversation_id=%s AND owner_id=%s ORDER BY id",
            (conversation_id, owner),
        )

    @app.delete("/api/conversations/{conversation_id}")
    def delete_conversation(conversation_id: UUID, owner=Depends(principal)):
        with db.connect() as conn:
            if conn.execute(
                "SELECT 1 FROM runs WHERE conversation_id=%s AND owner_id=%s AND status IN ('queued','running','waiting_approval','uncertain')",
                (conversation_id, owner),
            ).fetchone():
                raise DomainError(
                    "Resolve or cancel active runs before deleting a conversation", 409
                )
            conn.execute(
                "UPDATE runs SET conversation_id=NULL WHERE conversation_id=%s AND owner_id=%s",
                (conversation_id, owner),
            )
            row = conn.execute(
                "DELETE FROM conversations WHERE id=%s AND owner_id=%s RETURNING id",
                (conversation_id, owner),
            ).fetchone()
            if not row:
                raise DomainError("Conversation not found", 404)
        return {"status": "deleted"}

    @app.get("/api/schedules", response_model=list[ScheduleView])
    def list_schedules(owner=Depends(principal)):
        return db.all(
            "SELECT * FROM schedules WHERE owner_id=%s ORDER BY next_at NULLS LAST", (owner,)
        )

    @app.post("/api/schedules", response_model=ScheduleView)
    def create_schedule(data: ScheduleInput, owner=Depends(principal)):
        return schedules.save(db, owner, data)

    @app.put("/api/schedules/{schedule_id}", response_model=ScheduleView)
    def edit_schedule(schedule_id: UUID, data: ScheduleEdit, owner=Depends(principal)):
        return schedules.save(db, owner, data, schedule_id)

    @app.delete("/api/schedules/{schedule_id}")
    def delete_schedule(schedule_id: UUID, owner=Depends(principal)):
        row = db.one(
            "DELETE FROM schedules WHERE id=%s AND owner_id=%s RETURNING id", (schedule_id, owner)
        )
        if not row:
            raise DomainError("Schedule not found", 404)
        return {"status": "deleted"}

    @app.post("/api/actions/{action_id}/approve", response_model=ActionView)
    def approve_action(action_id: UUID, data: Approval, owner=Depends(principal)):
        return broker.approve(owner, action_id, data.args_hash)

    @app.put("/api/actions/{action_id}", response_model=ActionView)
    def edit_action(action_id: UUID, data: Issue, owner=Depends(principal)):
        return broker.edit(owner, action_id, data)

    @app.post("/api/actions/{action_id}/reconcile", response_model=ActionView)
    def reconcile_action(action_id: UUID, owner=Depends(principal)):
        return broker.reconcile(owner, action_id)

    @app.get("/api/worker")
    def worker_status(owner=Depends(principal)):
        row = db.one(
            "SELECT max(seen_at) AS last_seen,bool_or(seen_at>now()-interval '30 seconds') AS online FROM worker_heartbeats"
        )
        return {"online": bool(row["online"]), "last_seen": row["last_seen"]}

    @app.get("/api/notes")
    def notes(owner=Depends(principal)):
        connections.get(owner, "workspace")
        return Workspace(settings.workspace_root, owner).list()

    @app.get("/api/notes/{name}")
    def read_note(name: str, owner=Depends(principal)):
        connections.get(owner, "workspace")
        return {"name": name, "content": Workspace(settings.workspace_root, owner).read(name)}

    @app.post("/api/notes")
    def create_note(data: Note, owner=Depends(principal)):
        row = connections.get(owner, "workspace")
        if not row["config"].get("enabled"):
            raise DomainError("Workspace disabled", 403)
        return Workspace(settings.workspace_root, owner).write(data.name, data.content)

    @app.get("/api/budgets")
    def budgets(owner=Depends(principal)):
        return {
            "max_steps": settings.max_steps,
            "max_run_seconds": settings.max_run_seconds,
            "max_daily_runs": settings.max_daily_runs,
            "max_daily_tokens": settings.max_daily_tokens,
            "daily_spend_limit_usd": settings.daily_spend_limit_usd,
            "usage": db.all(
                "SELECT model,tokens,cost_usd,latency_ms,created_at FROM usage WHERE owner_id=%s ORDER BY created_at DESC LIMIT 100",
                (owner,),
            ),
        }
