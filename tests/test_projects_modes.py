"""Project and mode boundaries use controlled transports, never live writes."""

import json
import uuid

import pytest
from test_workflows import app as workflow_app

from commander.auth import hasher
from commander.worker import Worker

app = workflow_app


def test_projects_revision_scope_and_conversation_isolation(app):
    client, vendor, owner, db = app
    response = client.get("/api/projects")
    assert response.status_code == 200
    default = response.json()[0]
    assert default["is_default"]
    project = client.post("/api/projects", json={"name": "Fictional Atlas"}).json()
    assert project["revision"] == 1
    edited = client.patch(
        "/api/projects/" + project["id"], json={"name": "Atlas renamed", "revision": 1}
    )
    assert edited.status_code == 200
    assert (
        client.patch(
            "/api/projects/" + project["id"], json={"name": "Stale", "revision": 1}
        ).status_code
        == 409
    )
    run = client.post(
        "/api/runs", json={"prompt": "Atlas context", "project_id": project["id"], "mode": "ask"}
    ).json()
    assert run["project_id"] == project["id"] and run["mode"] == "ask"
    assert client.get("/api/conversations", params={"project_id": default["id"]}).json() == []
    assert len(client.get("/api/runs", params={"project_id": project["id"]}).json()) == 1
    assert (
        client.post(
            "/api/runs",
            json={
                "prompt": "Wrong project",
                "project_id": default["id"],
                "conversation_id": run["conversation_id"],
            },
        ).status_code
        == 409
    )
    foreign = db.one(
        "INSERT INTO owners(username,password_hash) VALUES (%s,%s) RETURNING id",
        ("other", hasher.hash("fictional-password")),
    )
    other = db.one("SELECT id FROM projects WHERE owner_id=%s", (foreign["id"],))
    assert (
        client.post(
            "/api/runs", json={"prompt": "No access", "project_id": str(other["id"])}
        ).status_code
        == 404
    )
    assert (
        client.get("/api/conversations", params={"project_id": str(other["id"])}).status_code == 404
    )
    assert (
        client.patch(
            "/api/projects/" + str(other["id"]), json={"name": "Denied", "revision": 1}
        ).status_code
        == 404
    )
    assert client.post("/api/projects", json={"name": "   "}).status_code == 422


@pytest.mark.parametrize("mode", ["ask", "plan", "research"])
def test_modes_cannot_dispatch_note_or_issue_side_effects(app, settings, mode):
    client, vendor, owner, db = app
    vendor.completions = [
        {
            "tool_calls": [
                {
                    "id": "forbidden",
                    "type": "function",
                    "function": {
                        "name": "save_note",
                        "arguments": json.dumps(
                            {"name": "forbidden.md", "content": "must not write"}
                        ),
                    },
                }
            ]
        }
    ]
    created = client.post("/api/runs", json={"prompt": "Scope test", "mode": mode})
    assert created.status_code == 200
    run = created.json()
    Worker(settings, vendor.transport()).tick()
    result = client.get("/api/runs/" + run["id"]).json()
    assert result["status"] == "failed"
    assert not list(settings.workspace_root.rglob("forbidden.md"))
    assert db.one("SELECT count(*) AS n FROM actions WHERE run_id=%s", (run["id"],))["n"] == 0
    payload = [call[2] for call in vendor.calls if call[1].endswith("/chat/completions")][0]
    assert not any(
        t["function"]["name"] in ("save_note", "propose_issue") for t in payload.get("tools", [])
    )
    if mode == "ask":
        assert all(call[1].endswith("/chat/completions") for call in vendor.calls)


def test_plan_persists_and_unavailable_execution_fails_before_dispatch(app, settings):
    client, vendor, owner, db = app
    for mode in ("build", "review"):
        response = client.post("/api/runs", json={"prompt": "No sandbox", "mode": mode})
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "capability_unavailable"
    assert not vendor.calls
    created = client.post("/api/runs", json={"prompt": "Make a plan", "mode": "plan"}).json()
    Worker(settings, vendor.transport()).tick()
    result = client.get("/api/runs/" + created["id"]).json()
    assert result["status"] == "succeeded"
    assert any(e["kind"] == "plan_ready" for e in result["events"])
    assert (
        client.post(
            "/api/runs",
            json={"prompt": "Wrong combination", "mode": "ask", "skill": "follow-through"},
        ).status_code
        == 422
    )


def test_project_memory_recall_and_explicit_precedence(app, settings):
    client, vendor, owner, db = app
    a = client.post("/api/projects", json={"name": "Atlas"}).json()["id"]
    b = client.post("/api/projects", json={"name": "Boreal"}).json()["id"]
    for scope, content in [
        (None, "Owner format"),
        (a, "Atlas confidential"),
        (b, "Boreal confidential"),
    ]:
        response = client.post(
            "/api/memory", json={"key": "format", "content": content, "project_id": scope}
        )
        assert response.status_code == 200, response.text
    run = client.post(
        "/api/runs", json={"prompt": "Recall preferences", "project_id": a, "mode": "ask"}
    ).json()
    Worker(settings, vendor.transport()).tick()
    payload = json.dumps([c[2] for c in vendor.calls if c[1].endswith("/chat/completions")][-1])
    assert "Atlas confidential" in payload and "Boreal confidential" not in payload
    assert "Owner format" not in payload
    assert len(client.get("/api/memory", params={"project_id": a}).json()) == 2
    assert client.get("/api/memory", params={"project_id": str(uuid.uuid4())}).status_code == 404
    assert client.get("/api/runs/" + run["id"]).json()["status"] == "succeeded"


def test_project_deletion_is_revision_bound_and_never_removes_retained_data(app):
    client, vendor, owner, db = app
    default = client.get("/api/projects").json()[0]
    assert (
        client.delete("/api/projects/" + default["id"], params={"revision": 1}).status_code == 409
    )
    project = client.post("/api/projects", json={"name": "Disposable empty"}).json()
    assert (
        client.delete("/api/projects/" + project["id"], params={"revision": 2}).status_code == 409
    )
    assert (
        client.delete("/api/projects/" + project["id"], params={"revision": 1}).status_code == 200
    )
    assert (
        client.delete("/api/projects/" + project["id"], params={"revision": 1}).status_code == 404
    )
    project = client.post("/api/projects", json={"name": "Retained memory"}).json()
    memory = client.post(
        "/api/memory",
        json={"key": "Scope", "content": "Scoped record", "project_id": project["id"]},
    ).json()
    assert (
        client.delete("/api/projects/" + project["id"], params={"revision": 1}).status_code == 409
    )
    # Editing through a legacy client must not widen project scope.
    updated = client.put(
        "/api/memory/" + memory["id"], json={"key": "Scope", "content": "Corrected", "revision": 1}
    )
    assert updated.status_code == 200 and updated.json()["project_id"] == project["id"]
    assert (
        client.put(
            "/api/memory/" + memory["id"],
            json={"key": "Scope", "content": "Widened", "revision": 2, "project_id": None},
        ).status_code
        == 409
    )


def test_schedule_occurrences_keep_project_scope(app, settings):
    from datetime import datetime, timedelta, timezone

    from commander.schedules import dispatch_due

    client, vendor, owner, db = app
    project = client.post("/api/projects", json={"name": "Scheduled project"}).json()
    scheduled = client.post(
        "/api/schedules",
        json={
            "prompt": "Project follow-through",
            "project_id": project["id"],
            "next_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
        },
    )
    assert scheduled.status_code == 200
    dispatch_due(db, settings)
    run = db.one("SELECT project_id,mode FROM runs WHERE schedule_id=%s", (scheduled.json()["id"],))
    assert str(run["project_id"]) == project["id"] and run["mode"] == "automate"
    assert len(client.get("/api/schedules", params={"project_id": project["id"]}).json()) == 1
