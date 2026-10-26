from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from commander.api import create_app
from commander.contracts import MemoryInput
from commander.memory import recall, save_memory
from commander.worker import Worker

pytest_plugins = ["test_workflows"]


def test_expired_explicit_does_not_suppress_active_inferred(app):
    _, _, owner, db = app
    save_memory(db, owner, MemoryInput(kind="inferred", key="format", content="short"))
    save_memory(
        db,
        owner,
        MemoryInput(
            key="format", content="long", expires_at=datetime.now(timezone.utc) - timedelta(days=1)
        ),
    )
    assert [r["content"] for r in recall(db, owner)] == ["short"]
    save_memory(db, owner, MemoryInput(kind="inferred", key="other", content="new"))


def test_stale_connection_cannot_restore_revoked_secret(app):
    client, _, _, _ = app
    row = client.get("/api/connections").json()[0]
    client.delete("/api/connections/nebius")
    response = client.put("/api/connections/nebius", json={"revision": row["revision"]})
    assert response.status_code == 409
    assert client.get("/api/connections").json()[0]["status"] == "revoked"


def test_settings_revision_limits_restart_and_snapshot(app, settings):
    client, vendor, owner, db = app
    response = client.get("/api/settings")
    assert response.status_code == 200
    initial = response.json()
    assert initial["revision"] == 0
    assert client.patch("/api/settings", json={"revision": 0, "max_steps": 10}).status_code == 422
    saved = client.patch(
        "/api/settings", json={"revision": 0, "max_steps": 2, "max_output_tokens": 512}
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["effective"]["max_steps"] == 2
    assert client.patch("/api/settings", json={"revision": 0, "max_steps": 1}).status_code == 409
    queued = client.post("/api/runs", json={"prompt": "Remember this configuration"}).json()
    row = db.one("SELECT * FROM runs WHERE id=%s", (queued["id"],))
    assert row["settings_snapshot"]["max_output_tokens"] == 512
    assert (
        client.patch("/api/settings", json={"revision": 1, "max_output_tokens": 1024}).status_code
        == 200
    )
    Worker(settings, vendor.transport()).tick()
    body = [v[2] for v in vendor.calls if v[1].endswith("/chat/completions")][-1]
    assert body["max_tokens"] == 512
    with TestClient(create_app(settings, vendor.transport())) as restarted:
        login = restarted.post(
            "/api/auth/login", json={"username": "owner", "password": "fictional-test-password"}
        )
        assert login.status_code == 200
        assert restarted.get("/api/settings").json()["effective"]["max_output_tokens"] == 1024
    status = client.get("/api/system/status")
    assert status.status_code == 200
    assert "fixture-canary-secret" not in status.text + saved.text


def test_settings_model_validation_and_boundary_errors(app):
    client, vendor, _, _ = app
    models = client.get("/api/models?provider=nebius")
    assert models.status_code == 200
    assert models.json()["models"] == ["nvidia/nemotron-3-super-120b-a12b"]
    for body in (
        {"encryption_key": "secret"},
        {"nebius_base_url": "http://127.0.0.1"},
        {"max_steps": None},
    ):
        assert client.patch("/api/settings", json={"revision": 0, **body}).status_code == 422
    unavailable = client.patch(
        "/api/settings", json={"revision": 0, "nebius_model": "nvidia/missing"}
    )
    assert unavailable.status_code == 502
    assert client.get("/api/settings").json()["revision"] == 0
    no_csrf = client.headers.pop("X-CSRF-Token")
    assert client.patch("/api/settings", json={"revision": 0, "max_steps": 1}).status_code == 403
    client.headers["X-CSRF-Token"] = no_csrf


def test_connection_concurrent_edits_have_one_winner(app, settings):
    from concurrent.futures import ThreadPoolExecutor

    from commander.connections import Connections
    from commander.contracts import ConnectionInput
    from commander.errors import DomainError

    _, _, owner, db = app

    def change(secret):
        try:
            Connections(db, settings).save(
                owner, "nebius", ConnectionInput(revision=1, secret=secret)
            )
            return 200
        except DomainError as error:
            return error.status

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(change, ["fictional-secret-a", "fictional-secret-b"])) == [200, 409]


def test_settings_owner_isolation_and_schedule_snapshot(app, settings):
    from commander.auth import hasher
    from commander.preferences import resolve
    from commander.schedules import dispatch_due

    client, _, owner, db = app
    other = db.one(
        "INSERT INTO owners(username,password_hash) VALUES (%s,%s) RETURNING id",
        ("other", hasher.hash("fictional-other-password")),
    )["id"]
    assert client.patch("/api/settings", json={"revision": 0, "max_steps": 2}).status_code == 200
    assert resolve(db, settings, other).max_steps == settings.max_steps
    assert (
        client.patch(
            "/api/settings", json={"revision": 1, "owner_id": str(other), "max_steps": 1}
        ).status_code
        == 422
    )
    due = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    assert (
        client.post(
            "/api/schedules", json={"prompt": "Scheduled snapshot", "next_at": due}
        ).status_code
        == 200
    )
    dispatch_due(db, settings)
    row = db.one(
        "SELECT settings_snapshot FROM runs WHERE owner_id=%s AND schedule_id IS NOT NULL", (owner,)
    )
    assert row["settings_snapshot"]["max_steps"] == 2


def test_selected_model_requires_revalidation_after_secret_change(app, settings):
    import httpx

    from commander.connections import Connections
    from commander.contracts import ConnectionInput
    from commander.preferences import SettingsPatch, update

    client, vendor, owner, db = app

    def models(request):
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "nvidia/alternate"}]})
        return vendor.handle(request)

    transport = httpx.MockTransport(models)
    update(
        db, settings, owner, SettingsPatch(revision=0, nebius_model="nvidia/alternate"), transport
    )
    client.post("/api/runs", json={"prompt": "Use verified alternate"}).raise_for_status()
    Worker(settings, transport).tick()
    assert client.get("/api/runs").json()[0]["status"] == "succeeded"
    Connections(db, settings).save(
        owner, "nebius", ConnectionInput(revision=1, secret="fictional-replacement")
    )
    before = len(vendor.calls)
    client.post("/api/runs", json={"prompt": "Must require validation"}).raise_for_status()
    Worker(settings, transport).tick()
    assert client.get("/api/runs").json()[0]["status"] == "failed"
    assert len(vendor.calls) == before


def test_context_reduction_preserves_current_request_and_records_omission(app, settings):
    import json

    from commander.broker import tools_for
    from commander.contracts import RunInput
    from commander.engine import Engine
    from commander.runs import enqueue

    _, _, owner, db = app
    for i in range(8):
        save_memory(db, owner, MemoryInput(key=f"preference-{i}", content="x" * 1000))
    settings = settings.model_copy(update={"max_context_chars": 4000})
    run = enqueue(db, settings, owner, RunInput(prompt="Keep this current question"))
    messages = Engine(db, settings).context(run)
    assert messages[-1]["content"] == "Keep this current question"
    assert len(json.dumps(messages)) + len(json.dumps(tools_for("conversation"))) <= 4000
    assert db.one("SELECT 1 FROM events WHERE run_id=%s AND kind='context_reduced'", (run["id"],))


def test_skill_step_ceiling_is_enforced(app, settings):
    import json

    client, vendor, _, _ = app
    settings = settings.model_copy(update={"max_steps": 10})
    vendor.completions = [
        {
            "tool_calls": [
                {
                    "id": str(i),
                    "type": "function",
                    "function": {"name": "github_read", "arguments": json.dumps({})},
                }
            ]
        }
        for i in range(10)
    ]
    client.post(
        "/api/runs", json={"skill": "engineering-briefing", "prompt": "Bounded reads only"}
    ).raise_for_status()
    Worker(settings, vendor.transport()).tick()
    assert len([c for c in vendor.calls if c[1].endswith("/chat/completions")]) == 5
    assert client.get("/api/runs").json()[0]["status"] == "failed"


def test_tighter_current_limit_applies_to_queued_snapshot(app, settings):
    client, vendor, _, _ = app
    queued = client.post("/api/runs", json={"prompt": "Queued before lower token cap"}).json()
    client.patch("/api/settings", json={"revision": 0, "max_output_tokens": 256}).raise_for_status()
    Worker(settings, vendor.transport()).tick()
    assert client.get("/api/runs/" + queued["id"]).json()["status"] == "succeeded"
    body = [c[2] for c in vendor.calls if c[1].endswith("/chat/completions")][-1]
    assert body["max_tokens"] == 256


def test_unknown_usage_keeps_original_reservation_after_limits_lower(app, settings):
    import pytest

    from commander.errors import DomainError
    from commander.inference import check_budget, complete
    from commander.providers import Provider

    _, vendor, owner, db = app
    vendor.mode = "outage"
    with pytest.raises(DomainError):
        complete(
            db,
            settings,
            Provider(settings, vendor.transport()),
            owner,
            "fictional-key",
            [{"role": "user", "content": "Fictional request with a lost response"}],
        )
    reduced = settings.model_copy(
        update={"max_context_chars": 4000, "max_output_tokens": 512, "max_daily_tokens": 20000}
    )
    with pytest.raises(DomainError, match="Daily token budget reached"):
        check_budget(db, reduced, owner)
