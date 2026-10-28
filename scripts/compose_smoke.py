"""Probe an explicitly isolated releasecheck Compose deployment; never external writes."""

import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import dotenv_values


def isolated_target():
    """Reject accidental use against an owner deployment before creating anything."""
    error = "Use the isolated clean-release runner; standalone smoke targets are denied"
    root = Path.cwd().resolve()
    base = os.getenv("COMPOSE_SMOKE_URL")
    project = os.getenv("COMPOSE_PROJECT_NAME", "")
    marker = root / ".runtime/compose-smoke-isolation.json"
    if (
        base != "http://localhost:8002"
        or not re.fullmatch(r"thecommander-cleancheck-[0-9a-f]{10}", project)
        or os.getenv("COMPOSE_SMOKE_ROOT") != str(root)
        or not root.name.startswith("thecommander-cleancheck-")
        or marker.is_symlink()
    ):
        raise SystemExit(error)
    try:
        expected = {"root": str(root), "project": project, "url": base}
        if json.loads(marker.read_text()) != expected:
            raise ValueError("Isolation marker mismatch")
    except (OSError, ValueError):
        raise SystemExit(error) from None
    return base, project


def main():
    base, project = isolated_target()
    Path(".runtime").mkdir(exist_ok=True)
    password = secrets.token_urlsafe(24)
    config = dotenv_values(".env.runtime")
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "deployment": project,
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
        state_path = Path(".runtime/releasecheck-state.json")
        if state_path.exists():
            previous = json.loads(state_path.read_text())
            assert any(
                x["id"] == previous["memory_id"] for x in client.get("/api/memory/export").json()
            )
            assert (
                client.get("/api/notes/" + previous["note"]).json()["content"]
                == "Fictional Compose note"
            )
            assert (
                client.get("/api/settings").json()["effective"]["max_steps"]
                == previous["max_steps"]
            )
            report["checks"].append("retained_volume_memory_note_settings_after_recreate")
        settings = client.get("/api/settings").json()
        saved = client.patch(
            "/api/settings",
            json={
                "revision": settings["revision"],
                "max_steps": min(2, settings["ceilings"]["max_steps"]),
            },
        )
        saved.raise_for_status()
        report["checks"].append("persistent_owner_settings")
        key = "releasecheck-" + secrets.token_hex(4)
        memory = client.post(
            "/api/memory", json={"key": key, "content": "Fictional Compose verification"}
        )
        memory.raise_for_status()
        assert any(x["id"] == memory.json()["id"] for x in client.get("/api/memory/export").json())
        report["checks"].append("persisted_memory_export")
        client.put(
            "/api/connections/workspace",
            json={
                "enabled": True,
                "revision": next(
                    c["revision"]
                    for c in client.get("/api/connections").json()
                    if c["kind"] == "workspace"
                ),
            },
        ).raise_for_status()
        note = client.post(
            "/api/notes", json={"name": key + ".md", "content": "Fictional Compose note"}
        )
        note.raise_for_status()
        assert note.json()["verified"]
        report["checks"].append("persistent_workspace_note")
        state_path.write_text(
            json.dumps(
                {
                    "memory_id": memory.json()["id"],
                    "note": key + ".md",
                    "max_steps": saved.json()["effective"]["max_steps"],
                }
            )
        )
        state_path.chmod(0o600)
        heartbeat = client.get("/api/worker").json()
        assert heartbeat["online"]
        report["checks"].append("separate_worker_heartbeat")
        client.post("/api/auth/logout").raise_for_status()
        assert client.get("/api/memory").status_code == 401
        report["checks"].append("session_revocation")
    Path("docs/evidence/compose-smoke.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
