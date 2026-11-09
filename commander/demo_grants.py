"""Expiring, priced judge authority; no credential copies or public registration."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID

import psycopg
from fastapi import Depends
from pydantic import BaseModel, Field

from commander import auth
from commander.connections import owner_lock
from commander.contracts import Strict
from commander.db import json
from commander.errors import DomainError
from commander.settings import inference_model

Money = Annotated[float, Field(gt=0, le=100, allow_inf_nan=False)]


class ModelPrice(Strict):
    input_usd_per_million: Money
    output_usd_per_million: Money


class GrantInput(Strict):
    owner_id: UUID
    expires_hours: int = Field(default=24, ge=1, le=168)
    model: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9_.:/-]+$")
    prices: dict[str, ModelPrice] = Field(min_length=1, max_length=4)
    max_usd: Money
    max_tokens: int = Field(gt=0, le=10_000_000)
    max_runs: int = Field(gt=0, le=100)
    aggregate_max_usd: Money
    aggregate_max_tokens: int = Field(gt=0, le=10_000_000)


class GrantView(BaseModel):
    id: UUID
    owner_id: UUID
    expires_at: datetime
    revoked_at: datetime | None
    model: str
    max_usd: float
    max_tokens: int
    max_runs: int


def current(db, owner):
    return db.one(
        """SELECT g.* FROM demo_provider_grants g
         JOIN owners recipient ON recipient.id=g.owner_id
         JOIN owners operator ON operator.id=g.operator_id
         JOIN connections c ON c.owner_id=g.operator_id AND c.kind='vultr'
         WHERE g.owner_id=%s AND g.revoked_at IS NULL AND g.expires_at>now()
         AND recipient.disabled_at IS NULL AND operator.disabled_at IS NULL AND operator.role='operator'
         AND c.status='validated' AND c.revision=g.connection_revision
         AND COALESCE((c.config->>'enabled')::boolean,true)
         AND (c.config->>'expires_at' IS NULL OR (c.config->>'expires_at')::timestamptz>now())
         AND NOT EXISTS(SELECT 1 FROM connections own WHERE own.owner_id=g.owner_id AND own.kind='vultr')""",
        (owner,),
    )


def connection(db, owner):
    grant = current(db, owner)
    if not grant:
        raise DomainError("Configure the vultr connection first", 409, "disconnected")
    row = db.one(
        "SELECT * FROM connections WHERE owner_id=%s AND kind='vultr'", (grant["operator_id"],)
    )
    expiry = row["config"].get("expires_at")
    if not row["config"].get("enabled", True) or (
        expiry and datetime.fromisoformat(expiry) <= datetime.now(timezone.utc)
    ):
        raise DomainError("Demo provider is unavailable", 409, "revoked")
    return {
        **row,
        "config": {
            **row["config"],
            "demo_grant_id": str(grant["id"]),
            "validated_model": grant["model"],
        },
    }


def create(db, operator, data):
    try:
        return _create(db, operator, data)
    except psycopg.errors.UniqueViolation:
        raise DomainError("This account already has a demo grant", 409, "grant_conflict") from None


def _create(db, operator, data):
    auth.require_operator(db, operator)
    if (
        data.model not in data.prices
        or data.max_usd > data.aggregate_max_usd
        or data.max_tokens > data.aggregate_max_tokens
    ):
        raise DomainError("Grant must fit the explicit priced pool", 422, "invalid_grant")
    with owner_lock(db, operator):
        auth.require_operator(db, operator)
        with db.connect() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(714896)")
            recipient = conn.execute(
                """SELECT o.id FROM owners o JOIN account_invitations i ON i.consumed_by=o.id
                 WHERE o.id=%s AND o.role='personal' AND o.disabled_at IS NULL
                 AND i.purpose='judge' AND i.revoked_at IS NULL FOR SHARE OF o""",
                (data.owner_id,),
            ).fetchone()
            source = conn.execute(
                "SELECT * FROM connections WHERE owner_id=%s AND kind='vultr' AND status='validated'",
                (operator,),
            ).fetchone()
            if not recipient or not source or source["config"].get("validated_model") != data.model:
                raise DomainError(
                    "Active judge account and validated Vultr model required",
                    409,
                    "validation_required",
                )
            # A pool is immutable: increasing spend requires a separate reviewed
            # change, never another invitation or grant creation.
            conn.execute(
                "INSERT INTO demo_provider_pools(operator_id,max_usd,max_tokens) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                (operator, data.aggregate_max_usd, data.aggregate_max_tokens),
            )
            pool = conn.execute(
                "SELECT * FROM demo_provider_pools WHERE operator_id=%s", (operator,)
            ).fetchone()
            if (
                float(pool["max_usd"]) != data.aggregate_max_usd
                or pool["max_tokens"] != data.aggregate_max_tokens
            ):
                raise DomainError(
                    "Existing aggregate budget cannot change through grant creation",
                    409,
                    "budget_conflict",
                )
            row = conn.execute(
                """INSERT INTO demo_provider_grants(owner_id,operator_id,connection_revision,model,prices,max_usd,max_tokens,max_runs,expires_at)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,now()+%s*interval '1 hour') RETURNING *""",
                (
                    data.owner_id,
                    operator,
                    source["revision"],
                    data.model,
                    json({model: price.model_dump() for model, price in data.prices.items()}),
                    data.max_usd,
                    data.max_tokens,
                    data.max_runs,
                    data.expires_hours,
                ),
            ).fetchone()
    return row


def reserve(conn, grant, settings, owner, run_id):
    """Called inside the same transaction as usage insertion, before any HTTP."""
    conn.execute("SELECT pg_advisory_xact_lock(714896)")
    # Revalidate after obtaining the shared pool lock, including operator key
    # revision/revocation. An unknown or expired grant must never fall back.
    active = conn.execute(
        """SELECT g.* FROM demo_provider_grants g JOIN owners o ON o.id=g.owner_id
         JOIN owners operator ON operator.id=g.operator_id
         JOIN connections c ON c.owner_id=g.operator_id AND c.kind='vultr'
         WHERE g.id=%s AND g.owner_id=%s AND g.expires_at>now() AND g.revoked_at IS NULL
         AND o.disabled_at IS NULL AND operator.disabled_at IS NULL AND operator.role='operator'
         AND c.status='validated' AND c.revision=g.connection_revision
         AND COALESCE((c.config->>'enabled')::boolean,true)
         AND (c.config->>'expires_at' IS NULL OR (c.config->>'expires_at')::timestamptz>now())""",
        (grant["id"], owner),
    ).fetchone()
    if not active:
        raise DomainError("Demo authorization expired or revoked", 409, "revoked")
    prices = active["prices"].get(inference_model(settings))
    if settings.inference_provider != "vultr" or not prices:
        raise DomainError("Demo model lacks reviewed prices", 409, "unknown_cost")
    reserved_tokens = settings.max_context_chars + settings.max_output_tokens
    reserved_cost = (
        Decimal(str(prices["input_usd_per_million"])) * settings.max_context_chars
        + Decimal(str(prices["output_usd_per_million"])) * settings.max_output_tokens
    ) / 1_000_000
    rows = conn.execute(
        """SELECT u.*,g.operator_id FROM usage u JOIN demo_provider_grants g ON g.id=u.demo_grant_id
         WHERE g.operator_id=%s""",
        (active["operator_id"],),
    ).fetchall()
    owned = [row for row in rows if row["demo_grant_id"] == active["id"]]
    pool = conn.execute(
        "SELECT * FROM demo_provider_pools WHERE operator_id=%s", (active["operator_id"],)
    ).fetchone()
    for records, limits in ((rows, pool), (owned, active)):
        tokens = sum(
            (row["tokens"] or {}).get("total_tokens", row["reserved_tokens"]) for row in records
        )
        # Unknown completion cost remains fully reserved, including transport
        # errors and malformed/missing usage; no automatic retry refunds.
        cost = sum(
            (row["cost_usd"] if row["cost_usd"] is not None else row["reserved_cost_usd"])
            for row in records
        )
        if (
            tokens + reserved_tokens > limits["max_tokens"]
            or cost + reserved_cost > limits["max_usd"]
        ):
            raise DomainError("Demo budget exhausted", 429, "budget_exceeded")
    if (
        run_id
        and run_id not in {row["run_id"] for row in owned}
        and len({row["run_id"] for row in owned if row["run_id"]}) >= active["max_runs"]
    ):
        raise DomainError("Demo run allowance exhausted", 429, "budget_exceeded")
    return active["id"], reserved_cost, prices


def require_dispatch(db, owner):
    auth.require_active(db, owner)
    own = db.one("SELECT * FROM connections WHERE owner_id=%s AND kind='vultr'", (owner,))
    if own:
        expiry = own["config"].get("expires_at")
        if (
            own["status"] != "validated"
            or not own["config"].get("enabled", True)
            or (expiry and datetime.fromisoformat(expiry) <= datetime.now(timezone.utc))
        ):
            raise DomainError("Validated Vultr authority required", 409, "revoked")
        return
    grant = db.one("SELECT 1 FROM demo_provider_grants WHERE owner_id=%s", (owner,))
    if grant:
        connection(db, owner)  # Rechecks expiry, source key revision and status.


def check_admission(db, owner, *, conn=None):
    if db.one("SELECT 1 FROM demo_provider_grants WHERE owner_id=%s", (owner,)):
        require_dispatch(db, owner)
    grant = current(db, owner)
    if not grant:
        return
    query = """SELECT (SELECT count(*) FROM runs WHERE owner_id=%s AND created_at>=%s)
     +(SELECT count(*) FROM sandbox_jobs WHERE owner_id=%s AND created_at>=%s) AS n"""
    params = (owner, grant["created_at"], owner, grant["created_at"])
    count = conn.execute(query, params).fetchone() if conn else db.one(query, params)
    if count["n"] >= grant["max_runs"]:
        raise DomainError("Demo run allowance exhausted", 429, "budget_exceeded")


def install_routes(app, db, operator_dependency):
    @app.get("/api/admin/demo-grants", response_model=list[GrantView])
    def grants(operator=Depends(operator_dependency)):
        return db.all(
            "SELECT * FROM demo_provider_grants WHERE operator_id=%s ORDER BY created_at DESC",
            (operator,),
        )

    @app.post("/api/admin/demo-grants", response_model=GrantView)
    def grant(data: GrantInput, operator=Depends(operator_dependency)):
        return create(db, operator, data)

    @app.delete("/api/admin/demo-grants/{grant_id}")
    def revoke(grant_id: UUID, operator=Depends(operator_dependency)):
        target = db.one(
            "SELECT owner_id FROM demo_provider_grants WHERE id=%s AND operator_id=%s",
            (grant_id, operator),
        )
        if not target:
            raise DomainError("Grant not found", 404)
        # Match inference's recipient->operator lock order. Revoke waits for an
        # already authorized HTTP call, then closes all future dispatch.
        with owner_lock(db, target["owner_id"]), owner_lock(db, operator):
            auth.require_operator(db, operator)
            with db.connect() as conn:
                conn.execute("SELECT pg_advisory_xact_lock(714896)")
                conn.execute(
                    "UPDATE demo_provider_grants SET revoked_at=now() WHERE id=%s AND operator_id=%s",
                    (grant_id, operator),
                )
                if not conn.execute(
                    "SELECT 1 FROM connections WHERE owner_id=%s AND kind='vultr'",
                    (target["owner_id"],),
                ).fetchone():
                    conn.execute(
                        "UPDATE schedules SET paused=true,revision=revision+1 WHERE owner_id=%s",
                        (target["owner_id"],),
                    )
                    conn.execute(
                        "UPDATE sandbox_jobs SET status='cancelled',error='Demo authorization revoked',updated_at=now(),lease_token=NULL,lease_until=NULL WHERE owner_id=%s AND status IN ('queued','running','waiting_approval','approved')",
                        (target["owner_id"],),
                    )
                    conn.execute(
                        "UPDATE runs SET status='cancelled',error='Demo authorization revoked',updated_at=now(),lease_token=NULL,lease_until=NULL WHERE owner_id=%s AND status IN ('queued','running','waiting_approval') AND settings_snapshot->>'inference_provider'='vultr'",
                        (target["owner_id"],),
                    )
                    conn.execute(
                        "UPDATE actions SET status='denied',error='Demo authorization revoked' WHERE owner_id=%s AND status IN ('pending','approved') AND run_id IN (SELECT id FROM runs WHERE owner_id=%s AND status='cancelled')",
                        (target["owner_id"], target["owner_id"]),
                    )
        return {"status": "revoked"}
