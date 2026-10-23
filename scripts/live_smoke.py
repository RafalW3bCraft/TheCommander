"""Explicit live, read-only provider smoke. No GitHub writes. No private context."""

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from commander.connections import usable_secret
from commander.providers import Provider
from commander.settings import Settings

s = Settings()
p = Provider(s)
report = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "endpoint_host": urlparse(s.nebius_base_url).hostname,
    "model": s.nebius_model,
    "github": "not run: token/repository/write authorization required",
    "tavily": "not run: real TAVILY_API_KEY required",
    "checks": [],
}
if not usable_secret(s.nebius_api_key):
    report["checks"].append(
        {"check": "nebius", "status": "blocked", "reason": "NEBIUS_API_KEY missing/placeholder"}
    )
else:
    try:
        models = p.request(
            "GET", s.nebius_base_url.rstrip("/") + "/models", s.nebius_api_key, retry=True
        )
        available = s.nebius_model in [m["id"] for m in models.get("data", [])]
        report["checks"].append({"check": "model_list", "available": available})
        if available:
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "echo_check",
                        "description": "Return a harmless verification word",
                        "parameters": {
                            "type": "object",
                            "properties": {"word": {"type": "string"}},
                            "required": ["word"],
                            "additionalProperties": False,
                        },
                    },
                }
            ]
            messages = [
                {
                    "role": "user",
                    "content": "For a bounded integration test, call echo_check with word verified. Do not just describe the call.",
                }
            ]
            msg, usage, latency = p.completion(s.nebius_api_key, messages, tools, timeout=60)
            calls = msg.get("tool_calls", [])
            valid = False
            if len(calls) == 1 and calls[0]["function"]["name"] == "echo_check":
                args = json.loads(calls[0]["function"]["arguments"])
                valid = args == {"word": "verified"}
            report["checks"].append(
                {"check": "tool_proposal", "valid": valid, "usage": usage, "latency_ms": latency}
            )
            if valid:
                messages.append(
                    {"role": "assistant", "content": msg.get("content"), "tool_calls": calls}
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": calls[0]["id"],
                        "content": json.dumps({"word": "verified"}),
                    }
                )
                final, usage, latency = p.completion(s.nebius_api_key, messages, timeout=60)
                report["checks"].append(
                    {
                        "check": "tool_result_roundtrip",
                        "nonempty_result": bool(final.get("content")),
                        "usage": usage,
                        "latency_ms": latency,
                    }
                )
    except Exception as exc:
        report["checks"].append(
            {
                "check": "nebius_request",
                "status": "failed",
                "error_code": getattr(exc, "code", type(exc).__name__),
                "message": getattr(exc, "message", "Request failed; no credential data recorded"),
            }
        )
Path("docs/evidence").mkdir(exist_ok=True)
Path("docs/evidence/live-smoke.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
