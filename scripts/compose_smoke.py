"""Probe an explicitly isolated releasecheck Compose deployment; never external writes."""

import json
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import dotenv_values

base = os.getenv("COMPOSE_SMOKE_URL", "http://localhost:8000")
Path(".runtime").mkdir(exist_ok=True)
password = secrets.token_urlsafe(24)
config = dotenv_values(".env.runtime")
report = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "deployment": os.getenv("COMPOSE_PROJECT_NAME", "thecommander-releasecheck"),
    "checks": [],
}
with httpx.Client(base_url=base, timeout=10) as client:
    for _ in range(30):
        try:
            if client.get("/health/ready").status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(1)
    response = client.get("/health/ready")
    response.raise_for_status()
    report["checks"].append("database_readiness")
    assert client.get("/").status_code == 200
    report["checks"].append("production_frontend_served")
    status = client.get("/api/auth/status").json()
    if not status["bootstrap_required"]:
        password = Path(".runtime/releasecheck-password").read_text()
        auth = client.post(
            "/api/auth/login", json={"username": "releasecheck-owner", "password": password}
        )
    else:
        auth = client.post(
            "/api/auth/bootstrap",
            json={
                "username": "releasecheck-owner",
                "password": password,
                "token": config["BOOTSTRAP_TOKEN"],
            },
        )
        Path(".runtime/releasecheck-password").write_text(password)
        Path(".runtime/releasecheck-password").chmod(0o600)
    auth.raise_for_status()
    client.headers["X-CSRF-Token"] = auth.json()["csrf"]
    report["checks"].append("secure_owner_login")
    key = "releasecheck-" + secrets.token_hex(4)
    memory = client.post(
        "/api/memory", json={"key": key, "content": "Fictional Compose verification"}
    )
    memory.raise_for_status()
    assert any(x["id"] == memory.json()["id"] for x in client.get("/api/memory/export").json())
    report["checks"].append("persisted_memory_export")
    client.put("/api/connections/workspace", json={"enabled": True}).raise_for_status()
    note = client.post(
        "/api/notes", json={"name": key + ".md", "content": "Fictional Compose note"}
    )
    note.raise_for_status()
    assert note.json()["verified"]
    report["checks"].append("persistent_workspace_note")
    heartbeat = client.get("/api/worker").json()
    assert heartbeat["online"]
    report["checks"].append("separate_worker_heartbeat")
    client.post("/api/auth/logout").raise_for_status()
    assert client.get("/api/memory").status_code == 401
    report["checks"].append("session_revocation")
Path("docs/evidence/compose-smoke.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
