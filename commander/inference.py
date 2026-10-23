"""Shared budget and usage accounting for every application inference dispatch."""

import json as stdjson

from commander.db import json
from commander.errors import DomainError


def check_budget(db, settings, owner):
    rows = db.all(
        "SELECT tokens,cost_usd FROM usage WHERE owner_id=%s AND created_at>now()-interval '1 day'",
        (owner,),
    )
    maximum = settings.max_context_chars + settings.max_output_tokens
    tokens = sum((r["tokens"] or {}).get("total_tokens", maximum) for r in rows)
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
    # Caller holds owner dispatch lock. Persist unknown usage before sending;
    # interruption/lost response conservatively consumes the maximum token reserve.
    check_budget(db, settings, owner)
    if len(stdjson.dumps(messages)) + len(stdjson.dumps(tools)) > settings.max_context_chars:
        raise DomainError("Context budget exceeded; shorten the task", 422, "budget_exceeded")
    record = db.one(
        "INSERT INTO usage(owner_id,run_id,model,latency_ms) VALUES (%s,%s,%s,0) RETURNING id",
        (owner, run_id, settings.nebius_model),
    )
    message, usage, latency = provider.completion(secret, messages, tools, timeout)
    if usage is not None and (
        not isinstance(usage, dict)
        or any(
            not isinstance(usage.get(k), int) or usage[k] < 0
            for k in ("prompt_tokens", "completion_tokens", "total_tokens")
        )
    ):
        raise DomainError(
            "Provider returned invalid usage; consumption remains unknown", 502, "malformed_usage"
        )
    cost = None
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
