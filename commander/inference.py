"""Shared budget and usage accounting for every application inference dispatch."""

import json as stdjson
from contextlib import nullcontext

from commander import auth
from commander.db import json
from commander.errors import DomainError
from commander.settings import inference_model


def check_budget(db, settings, owner):
    rows = db.all(
        "SELECT tokens,cost_usd,reserved_tokens FROM usage WHERE owner_id=%s AND created_at>now()-interval '1 day'",
        (owner,),
    )
    maximum = settings.max_context_chars + settings.max_output_tokens
    tokens = sum((r["tokens"] or {}).get("total_tokens", r["reserved_tokens"]) for r in rows)
    if tokens + maximum > settings.max_daily_tokens:
        raise DomainError("Daily token budget reached", 429, "budget_exceeded")
    if settings.daily_spend_limit_usd is not None:
        if (
            settings.input_usd_per_million is None
            or settings.output_usd_per_million is None
            or any(r["cost_usd"] is None for r in rows)
        ):
            raise DomainError(
                "Spend enforcement requires verified pricing and usage; no request dispatched",
                409,
                "unknown_cost",
            )
        reserve = (
            settings.max_context_chars * settings.input_usd_per_million
            + settings.max_output_tokens * settings.output_usd_per_million
        ) / 1_000_000
        if sum(float(r["cost_usd"]) for r in rows) + reserve > settings.daily_spend_limit_usd:
            raise DomainError("Daily spend budget reached", 429, "budget_exceeded")


def complete(db, settings, provider, owner, secret, messages, tools=None, run_id=None, timeout=30):
    from commander.connections import owner_lock
    from commander.demo_grants import current

    grant = current(db, owner) if settings.inference_provider == "vultr" else None
    # A revoked/expired delegated account must not use a secret fetched just
    # before revocation. Personal credentials remain independent of demo grants.
    if (
        settings.inference_provider == "vultr"
        and not grant
        and db.one("SELECT 1 FROM demo_provider_grants WHERE owner_id=%s", (owner,))
        and not db.one("SELECT 1 FROM connections WHERE owner_id=%s AND kind='vultr'", (owner,))
    ):
        raise DomainError("Demo authorization expired or revoked", 409, "revoked")
    # Serialize operator revoke/disable/key changes against the whole HTTP call.
    with owner_lock(db, grant["operator_id"]) if grant else nullcontext():
        return _complete_locked(
            db, settings, provider, owner, secret, messages, tools, run_id, timeout, grant
        )


def _complete_locked(
    db, settings, provider, owner, secret, messages, tools, run_id, timeout, grant
):
    auth.require_active(db, owner)
    # Caller holds owner dispatch lock. Persist unknown usage before sending;
    # interruption/lost response conservatively consumes the maximum token reserve.
    if grant and inference_model(settings) in grant["prices"]:
        settings = settings.model_copy(update=grant["prices"][inference_model(settings)])
    check_budget(db, settings, owner)
    if len(stdjson.dumps(messages)) + len(stdjson.dumps(tools)) > settings.max_context_chars:
        raise DomainError("Context budget exceeded; shorten the task", 422, "budget_exceeded")
    prices = None
    with db.connect() as conn:
        grant_id, reserved_cost = None, None
        if grant:
            from commander.demo_grants import reserve

            grant_id, reserved_cost, prices = reserve(conn, grant, settings, owner, run_id)
        record = conn.execute(
            """INSERT INTO usage(owner_id,run_id,model,provider,latency_ms,reserved_tokens,demo_grant_id,reserved_cost_usd)
             VALUES (%s,%s,%s,%s,0,%s,%s,%s) RETURNING id""",
            (
                owner,
                run_id,
                inference_model(settings),
                settings.inference_provider,
                settings.max_context_chars + settings.max_output_tokens,
                grant_id,
                reserved_cost,
            ),
        ).fetchone()
    message, usage, latency = provider.completion(secret, messages, tools, timeout)
    if usage is not None and (
        not isinstance(usage, dict)
        or any(
            type(usage.get(k)) is not int or usage[k] < 0
            for k in ("prompt_tokens", "completion_tokens", "total_tokens")
        )
    ):
        raise DomainError(
            "Provider returned invalid usage; consumption remains unknown", 502, "malformed_usage"
        )
    cost = None
    if prices:
        settings = settings.model_copy(update=prices)
    if (
        usage
        and settings.input_usd_per_million is not None
        and settings.output_usd_per_million is not None
    ):
        cost = (
            usage["prompt_tokens"] * settings.input_usd_per_million
            + usage["completion_tokens"] * settings.output_usd_per_million
        ) / 1_000_000
    db.one(
        "UPDATE usage SET tokens=%s,cost_usd=%s,latency_ms=%s WHERE id=%s RETURNING id",
        (json(usage), cost, latency, record["id"]),
    )
    return message, usage, latency, cost


def validate_model(db, settings, provider, owner, secret):
    """A validation proposal has no broker dispatch and cannot cause a tool effect."""
    if settings.inference_provider == "nebius":
        return complete(
            db,
            settings,
            provider,
            owner,
            secret,
            [{"role": "user", "content": "Reply with OK only."}],
        )
    tool = {
        "type": "function",
        "function": {
            "name": "validation_probe",
            "description": "Confirm supported tool-call syntax without executing any action.",
            "parameters": {
                "type": "object",
                "properties": {"ok": {"type": "boolean", "enum": [True]}},
                "required": ["ok"],
                "additionalProperties": False,
            },
        },
    }
    result = complete(
        db,
        settings,
        provider,
        owner,
        secret,
        [
            {
                "role": "user",
                "content": "Call validation_probe exactly once with ok=true. Do not answer in text.",
            }
        ],
        [tool],
    )
    try:
        calls = result[0].get("tool_calls", [])
        if (
            len(calls) != 1
            or calls[0]["function"]["name"] != "validation_probe"
            or stdjson.loads(calls[0]["function"]["arguments"]) != {"ok": True}
        ):
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise DomainError(
            "Selected model did not demonstrate the required tool capability",
            502,
            "unsupported_capability",
        ) from None
    return result
