"""Owner configuration, bounded by operator policy; never stores credentials."""

from typing import Literal

from pydantic import Field, model_validator

from commander.contracts import Strict
from commander.db import json
from commander.errors import DomainError

Endpoint = Literal[
    "https://api.tokenfactory.nebius.com/v1", "https://api.tokenfactory.us-central1.nebius.com/v1"
]
LIMITS = (
    "max_steps",
    "max_output_tokens",
    "max_context_chars",
    "max_run_seconds",
    "max_daily_runs",
    "max_daily_tokens",
)
FIELDS = (*LIMITS, "daily_spend_limit_usd", "nebius_model", "nebius_base_url")


class Preferences(Strict):
    nebius_model: str | None = Field(
        default=None, pattern=r"^nvidia/[A-Za-z0-9_.-]+$", max_length=200
    )
    nebius_base_url: Endpoint | None = None
    max_steps: int | None = Field(default=None, ge=1, le=10)
    max_output_tokens: int | None = Field(default=None, ge=128, le=8192)
    max_context_chars: int | None = Field(default=None, ge=4000, le=100000)
    max_run_seconds: int | None = Field(default=None, ge=30, le=600)
    max_daily_runs: int | None = Field(default=None, ge=1, le=1000)
    max_daily_tokens: int | None = Field(default=None, ge=1000)
    daily_spend_limit_usd: float | None = Field(default=None, gt=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def reject_null(self):
        if any(
            getattr(self, k) is None for k in self.model_fields_set if k != "daily_spend_limit_usd"
        ):
            raise ValueError("Only the optional spending limit may be null")
        return self


class SettingsPatch(Preferences):
    revision: int = Field(ge=0)


class SettingsView(Strict):
    revision: int
    preferences: Preferences
    effective: Preferences
    ceilings: Preferences


class ModelsView(Strict):
    models: list[str]


class SystemView(Strict):
    api: Literal["ready"]
    database: Literal["ready"]
    worker_online: bool
    production: bool
    configured: dict[str, bool]
    restart_required: list[str]


def values(settings):
    return {k: getattr(settings, k) for k in FIELDS}


def resolve(db, operator, owner, snapshot=None):
    row = db.one("SELECT * FROM owner_settings WHERE owner_id=%s", (owner,))
    current = {**values(operator), **(row["preferences"] if row else {})}
    selected = {**current, **(snapshot or {})}
    for k in LIMITS:
        selected[k] = min(selected[k], current[k], getattr(operator, k))
    caps = [
        v
        for v in (
            selected["daily_spend_limit_usd"],
            current["daily_spend_limit_usd"],
            operator.daily_spend_limit_usd,
        )
        if v is not None
    ]
    selected["daily_spend_limit_usd"] = min(caps) if caps else None
    if selected["nebius_model"] != operator.nebius_model:
        selected.update(input_usd_per_million=None, output_usd_per_million=None)
    return operator.model_copy(update=selected)


def view(db, operator, owner):
    row = db.one("SELECT * FROM owner_settings WHERE owner_id=%s", (owner,))
    return {
        "revision": row["revision"] if row else 0,
        "preferences": row["preferences"] if row else {},
        "effective": values(resolve(db, operator, owner)),
        "ceilings": values(operator),
    }


def discover(provider, settings, secret):
    data = provider.request(
        "GET", settings.nebius_base_url.rstrip("/") + "/models", secret, retry=True
    )
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("data"), list)
        or any(not isinstance(m, dict) or not isinstance(m.get("id"), str) for m in data["data"])
    ):
        raise DomainError("Provider returned malformed model data", 502, "malformed_response")
    return sorted({m["id"] for m in data["data"] if m["id"].startswith("nvidia/")})


def update(db, operator, owner, data, transport=None):
    from commander.connections import Connections, owner_lock
    from commander.inference import complete
    from commander.providers import Provider

    with owner_lock(db, owner):
        row = db.one("SELECT * FROM owner_settings WHERE owner_id=%s", (owner,))
        if data.revision != (row["revision"] if row else 0):
            raise DomainError("Settings changed; reload before saving", 409, "revision_conflict")
        changes = data.model_dump(exclude_unset=True, exclude={"revision"})
        for k in LIMITS:
            if k in changes and changes[k] > getattr(operator, k):
                raise DomainError("Requested limit exceeds the operator ceiling: " + k, 422)
        if (
            "daily_spend_limit_usd" in changes
            and operator.daily_spend_limit_usd is not None
            and (
                changes["daily_spend_limit_usd"] is None
                or changes["daily_spend_limit_usd"] > operator.daily_spend_limit_usd
            )
        ):
            raise DomainError("Spending limit cannot exceed the operator ceiling", 422)
        merged = {**(row["preferences"] if row else {}), **changes}
        before = resolve(db, operator, owner)
        candidate = operator.model_copy(update={**values(before), **changes})
        if candidate.nebius_model != operator.nebius_model:
            candidate = candidate.model_copy(
                update={"input_usd_per_million": None, "output_usd_per_million": None}
            )
        model_changed = any(
            getattr(candidate, k) != getattr(before, k) for k in ("nebius_model", "nebius_base_url")
        )
        if model_changed:
            connections = Connections(db, operator, transport)
            connection = connections.get(owner, "nebius")
            secret = connections.secret(connection)
            provider = Provider(candidate, transport)
            if candidate.nebius_model not in discover(provider, candidate, secret):
                raise DomainError(
                    "Selected NVIDIA model is unavailable to this account", 502, "unavailable_model"
                )
            complete(
                db,
                candidate,
                provider,
                owner,
                secret,
                [{"role": "user", "content": "Reply with OK only."}],
            )
        with db.connect() as conn:
            if model_changed:
                conn.execute(
                    "UPDATE connections SET status='validated',validated_at=now(),detail='Selected model validated',config=config || %s WHERE owner_id=%s AND kind='nebius'",
                    (
                        json(
                            {
                                "validated_model": candidate.nebius_model,
                                "validated_endpoint": candidate.nebius_base_url,
                            }
                        ),
                        owner,
                    ),
                )
            conn.execute(
                "INSERT INTO owner_settings(owner_id,preferences) VALUES (%s,%s) ON CONFLICT(owner_id) DO UPDATE SET preferences=EXCLUDED.preferences,revision=owner_settings.revision+1,updated_at=now()",
                (owner, json(merged)),
            )
    return view(db, operator, owner)
