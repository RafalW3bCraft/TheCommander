"""Bounded live Tavily validation and broker search using fictional local state."""

import json
import os
import secrets
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from fastapi.testclient import TestClient
from psycopg import sql

from commander.api import create_app
from commander.broker import Broker
from commander.connections import usable_secret
from commander.errors import DomainError
from commander.settings import Settings
from commander.worker import Worker


def main():
    cfg = Settings()
    if not usable_secret(cfg.tavily_api_key):
        raise SystemExit("A real TAVILY_API_KEY is required; no fixture substituted")
    cfg = cfg.model_copy(
        update={
            "database_url": os.environ["TEST_DATABASE_URL"],
            "database_schema": "test_research_" + uuid.uuid4().hex,
        }
    )
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": "Tavily",
        "endpoint": "https://api.tavily.com/search",
        "approved_domains": ["docs.python.org"],
        "query": "Python asyncio task cancellation official documentation",
        "live": True,
        "external_writes": False,
    }
    try:
        with TestClient(create_app(cfg)) as client:
            auth = client.post(
                "/api/auth/bootstrap",
                json={
                    "username": "fictional-research-owner",
                    "password": secrets.token_urlsafe(24),
                    "token": cfg.bootstrap_token,
                },
            )
            auth.raise_for_status()
            client.headers["X-CSRF-Token"] = auth.json()["csrf"]
            client.put(
                "/api/connections/tavily",
                json={"secret": cfg.tavily_api_key, "domains": report["approved_domains"]},
            ).raise_for_status()
            validation = client.post("/api/connections/tavily/validate")
            validation.raise_for_status()
            connection = next(row for row in validation.json() if row["kind"] == "tavily")
            report["validation_status"] = connection["status"]
            if connection["status"] != "validated":
                raise DomainError(connection["detail"], 502, connection["status"])
            queued = client.post(
                "/api/runs",
                json={"skill": "research-to-action", "prompt": report["query"]},
            )
            queued.raise_for_status()
            worker = Worker(cfg)
            run = worker.claim()
            started = time.monotonic()
            result = Broker(worker.db, cfg).call(run, "search", {"query": report["query"]})
            report["search_latency_ms"] = round((time.monotonic() - started) * 1000)
            detail = client.get("/api/runs/" + queued.json()["id"])
            detail.raise_for_status()
            evidence = detail.json()["evidence"]
            assert result and evidence
            assert all(row["url"].startswith("https://docs.python.org/") for row in evidence)
            assert all(row["fetched_at"] and row["excerpt"] for row in evidence)
            report["evidence"] = [
                {key: row[key] for key in ("url", "title", "fetched_at")} for row in evidence
            ]
            report["persisted_evidence_count"] = len(evidence)
            report["passed"] = True
            report["limit"] = (
                "Connector validation and authorized broker search; no full GitHub skill or issue write"
            )
            client.post("/api/runs/" + queued.json()["id"] + "/cancel").raise_for_status()
    except DomainError as exc:
        report.update(passed=False, error_code=exc.code, error=exc.message)
    finally:
        with psycopg.connect(cfg.database_url) as conn:
            conn.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    sql.Identifier(cfg.database_schema)
                )
            )
    Path("docs/evidence/live-research-smoke.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    if not report.get("passed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
