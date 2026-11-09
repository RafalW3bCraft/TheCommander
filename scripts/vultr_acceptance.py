"""Explicit, bounded live Vultr capability probes. No fallback and no secret output."""

import argparse
import base64
import fcntl
import hashlib
import json
import struct
import zlib
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from commander.connections import Connections
from commander.db import Database
from commander.errors import DomainError
from commander.preferences import resolve
from commander.providers import Provider
from commander.settings import Settings


def image():
    def chunk(kind, data):
        return (
            struct.pack("!I", len(data))
            + kind
            + data
            + struct.pack("!I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    row = b"\xff\x00\x00" * 64 + b"\x00\x00\xff" * 64
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!IIBBBBB", 128, 64, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress((b"\0" + row) * 64))
        + chunk(b"IEND", b"")
    )


def run(settings, db, owner, ledger):
    effective = resolve(db, settings, owner)
    secret = Connections(db, effective).secret(Connections(db, effective).get(owner, "vultr"))
    provider = Provider(effective.model_copy(update={"inference_provider": "vultr"}))
    catalog = provider.request("GET", "https://api.vultrinference.com/v1/models", secret)
    models = {row["id"]: row for row in catalog["data"]}
    picture = image()
    tool = {
        "type": "function",
        "function": {
            "name": "report_answer",
            "description": "Report the exact arithmetic result without executing anything.",
            "parameters": {
                "type": "object",
                "properties": {"answer": {"type": "integer", "enum": [42]}},
                "required": ["answer"],
                "additionalProperties": False,
            },
        },
    }
    cases = [
        (
            "text",
            effective.provider_model,
            [{"role": "user", "content": "Compute 6 * 7. Reply with only the integer."}],
            None,
        ),
        (
            "tools",
            effective.provider_model,
            [
                {
                    "role": "user",
                    "content": "Call report_answer exactly once with answer=42. No text response.",
                }
            ],
            [tool],
        ),
        (
            "vision",
            settings.sandbox_vision_model,
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Name the solid color of the LEFT half, then the RIGHT half. Reply exactly RED BLUE or BLUE RED.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/png;base64," + base64.b64encode(picture).decode()
                            },
                        },
                    ],
                }
            ],
            None,
        ),
    ]
    report = []
    for kind, model, messages, tools in cases:
        metadata = models[model]
        prompt = next(
            Decimal(p["cost_usd"]) * 1000000
            for m in metadata["input_modalities"]
            for p in m.get("pricing", [])
            if p["type"] == "prompt" and p["unit"] == "token"
        )
        output = next(
            Decimal(p["cost_usd"]) * 1000000
            for m in metadata["output_modalities"]
            for p in m.get("pricing", [])
            if p["type"] == "completion" and p["unit"] == "token"
        )
        reserve = (prompt * settings.max_context_chars + output * 2048) / 1000000
        entry = {
            "kind": kind,
            "model": model,
            "reserved_usd": float(reserve),
            "status": "reserved",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "prices_usd_per_million": {"input": float(prompt), "output": float(output)},
        }
        with ledger.open("a+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.seek(0)
            prior = json.loads(f.read() or "[]")
            if any(e["kind"] == kind and e["status"] == "pass" for e in prior):
                report.append(next(e for e in prior if e["kind"] == kind and e["status"] == "pass"))
                continue
            if sum(
                Decimal(str(e.get("cost_usd", e["reserved_usd"]))) for e in prior
            ) + reserve > Decimal("0.10"):
                raise DomainError(
                    "Live probe budget exhausted; inspect private ledger", 429, "budget_exceeded"
                )
            prior.append(entry)
            f.seek(0)
            f.truncate()
            f.write(json.dumps(prior))
            f.flush()
            try:
                current = effective.model_copy(
                    update={
                        "inference_provider": "vultr",
                        "provider_model": model,
                        "max_output_tokens": 2048,
                    }
                )
                message, usage, latency = Provider(current).completion(
                    secret, messages, tools, timeout=60
                )
                if kind == "tools":
                    calls = message.get("tool_calls", [])
                    matched = (
                        len(calls) == 1
                        and calls[0]["function"]["name"] == "report_answer"
                        and json.loads(calls[0]["function"]["arguments"]) == {"answer": 42}
                    )
                else:
                    matched = message.get("content", "").strip().upper() == (
                        "RED BLUE" if kind == "vision" else "42"
                    )
                entry.update(
                    status="pass" if matched else "fail",
                    fact_matched=matched,
                    duration_ms=latency,
                    tokens=usage,
                )
                if usage and all(
                    type(usage.get(k)) is int and usage[k] >= 0
                    for k in ["prompt_tokens", "completion_tokens", "total_tokens"]
                ):
                    entry["cost_usd"] = float(
                        (prompt * usage["prompt_tokens"] + output * usage["completion_tokens"])
                        / 1000000
                    )
                if kind == "vision":
                    entry["image_sha256"] = hashlib.sha256(picture).hexdigest()
            except DomainError as exc:
                entry.update(status="fail", error_code=exc.code)
            prior[-1] = entry
            f.seek(0)
            f.truncate()
            f.write(json.dumps(prior))
            f.flush()
            report.append(entry)
            if entry["status"] != "pass":
                break
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--ledger", default=".runtime/vultr-validation-ledger.json")
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("Use --execute only with an authorized inference budget")
    settings = Settings()
    db = Database(settings)
    owner = db.one(
        "SELECT id FROM owners WHERE role='operator' AND disabled_at IS NULL ORDER BY created_at,id LIMIT 1"
    )["id"]
    ledger = Path(args.ledger)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.touch(mode=0o600, exist_ok=True)
    report = run(settings, db, owner, ledger)
    print(json.dumps({"evidence_type": "real_vultr_service", "results": report}, indent=2))
    if len(report) != 3 or any(row["status"] != "pass" for row in report):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
