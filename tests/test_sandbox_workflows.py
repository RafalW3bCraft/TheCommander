"""Real PostgreSQL state transitions; inference and container effects are fixtures."""

import base64
import hashlib
import json
import uuid

import pytest
from test_workflows import app as workflow_app

from commander.db import json as jsonb
from commander.errors import DomainError
from commander.sandbox.worker import SandboxWorker

app = workflow_app


class FixtureRunner:
    def __init__(self):
        self.calls = []
        self.code_exits = [0]
        self.fail = False

    def execute(self, kind, payload, *, cancelled):
        self.calls.append((kind, payload))
        assert "fixture-canary-secret" not in payload
        if self.fail:
            raise DomainError("Controlled browser page changed", 422)
        receipt = {
            "destroyed": True,
            "exit_code": self.code_exits.pop(0) if kind == "code" else 0,
            "stop_reason": None,
            "evidence_type": "test_fixture",
        }
        screenshot = b"\xff\xd8\xfftest-fixture-only-not-a-live-screenshot"
        output = (
            "42\n"
            if kind == "code"
            else json.dumps(
                {
                    "url": "https://example.com/",
                    "title": "Fixture page",
                    "text": "A controlled form",
                    "screenshot": base64.b64encode(screenshot).decode(),
                    "screenshot_sha256": hashlib.sha256(screenshot).hexdigest(),
                    "page_sha256": "a" * 64,
                    "actions_executed": len(json.loads(payload)["steps"]),
                    "controls": [{"selector": "#name", "tag": "input"}],
                }
            )
        )
        return {
            "stdout": output,
            "stderr": "" if receipt["exit_code"] == 0 else "Controlled error",
            "receipt": receipt,
        }


@pytest.fixture
def sandbox(app, settings):
    client, vendor, owner, db = app
    settings.sandbox_enabled = True
    settings.sandbox_model = "fixture-text"
    settings.sandbox_vision_model = "fixture-vision"
    settings.sandbox_browser_domains = ["example.com"]
    assert (
        client.put("/api/connections/vultr", json={"secret": "fixture-canary-secret"}).status_code
        == 200
    )
    runner = FixtureRunner()
    worker = SandboxWorker(settings, db=db, runner=runner, transport=vendor.transport())
    project = client.get("/api/projects").json()[0]["id"]
    return client, vendor, owner, db, runner, worker, project


def enqueue(sandbox, kind="code"):
    client, _, _, _, _, _, project = sandbox
    response = client.post(
        "/api/sandbox/jobs",
        json={
            "kind": kind,
            "goal": "Compute the answer" if kind == "code" else "Fill the controlled form",
            "project_id": project,
            "url": "https://example.com/" if kind == "browser" else "",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def respond(vendor, *values):
    vendor.completions.extend({"content": json.dumps(value)} for value in values)


def test_code_real_state_and_receipt_roundtrip(sandbox):
    client, vendor, _, db, runner, worker, _ = sandbox
    respond(
        vendor,
        {"explanation": "Compute", "code": "print(42)"},
        {"verified": True, "explanation": "Actual output is 42"},
    )
    job = enqueue(sandbox)
    assert worker.tick()
    result = client.get("/api/sandbox/jobs/" + job).json()
    assert result["status"] == "succeeded" and result["evidence"]["stdout"] == "42\n"
    assert result["receipt"]["destroyed"] and len(runner.calls) == 1
    assert all(url.startswith("https://api.vultrinference.com/v1/") for _, url, _ in vendor.calls)
    assert db.one("SELECT count(*) AS n FROM usage WHERE provider='vultr'")["n"] == 2
    assert not worker.tick()


def test_code_repairs_once_using_actual_error(sandbox):
    client, vendor, _, _, runner, worker, _ = sandbox
    runner.code_exits = [1, 0]
    respond(
        vendor,
        {"explanation": "First", "code": "raise ValueError()"},
        {"explanation": "Repair", "code": "print(42)"},
        {"verified": True, "explanation": "Corrected output"},
    )
    job = enqueue(sandbox)
    worker.tick()
    assert client.get("/api/sandbox/jobs/" + job).json()["status"] == "succeeded"
    assert len(runner.calls) == 2
    requests = [body for _, url, body in vendor.calls if url.endswith("chat/completions")]
    assert "Controlled error" in json.dumps(requests[1])


def browser_ready(sandbox):
    client, vendor, _, _, runner, worker, _ = sandbox
    respond(
        vendor,
        {"verified": True, "explanation": "Form visible"},
        {
            "explanation": "Fill a public demo name",
            "steps": [{"action": "fill", "selector": "#name", "value": "Demo"}],
        },
    )
    job = enqueue(sandbox, "browser")
    worker.tick()
    row = client.get("/api/sandbox/jobs/" + job).json()
    assert row["status"] == "waiting_approval", row
    assert not json.loads(runner.calls[0][1])["approved"]
    assert not json.loads(runner.calls[0][1])["steps"]
    return job, row


def test_browser_observe_vision_exact_approval_execute_verify(sandbox):
    client, vendor, _, _, runner, worker, _ = sandbox
    job, row = browser_ready(sandbox)
    decision = {"digest": row["approval_digest"], "approve": True}
    assert (
        client.post(
            f"/api/sandbox/jobs/{job}/decision", json={**decision, "digest": "0" * 64}
        ).status_code
        == 409
    )
    assert client.post(f"/api/sandbox/jobs/{job}/decision", json=decision).status_code == 200
    assert client.post(f"/api/sandbox/jobs/{job}/decision", json=decision).status_code == 409
    respond(vendor, {"verified": True, "explanation": "Final form state visible"})
    worker.tick()
    result = client.get("/api/sandbox/jobs/" + job).json()
    assert result["status"] == "succeeded"
    final = json.loads(runner.calls[1][1])
    assert final["approved"] and final["expected_page_sha256"] == "a" * 64
    assert final["steps"] == row["plan"]["steps"]
    messages = [body for _, _, body in vendor.calls]
    assert any(isinstance(m["content"], list) for b in messages for m in b["messages"])


@pytest.mark.parametrize("operation", ["deny", "expire", "cancel", "mutate"])
def test_approval_never_authorizes_changed_expired_denied_cancelled_job(sandbox, operation):
    client, _, _, db, runner, worker, _ = sandbox
    job, row = browser_ready(sandbox)
    if operation == "deny":
        assert (
            client.post(
                f"/api/sandbox/jobs/{job}/decision",
                json={"digest": row["approval_digest"], "approve": False},
            ).status_code
            == 200
        )
    elif operation == "expire":
        db.one(
            "UPDATE sandbox_jobs SET approval_expires_at=now()-interval '1 second' WHERE id=%s RETURNING id",
            (job,),
        )
        assert (
            client.post(
                f"/api/sandbox/jobs/{job}/decision",
                json={"digest": row["approval_digest"], "approve": True},
            ).status_code
            == 409
        )
    elif operation == "cancel":
        assert client.post(f"/api/sandbox/jobs/{job}/cancel").json()["status"] == "cancelled"
    else:
        client.post(
            f"/api/sandbox/jobs/{job}/decision",
            json={"digest": row["approval_digest"], "approve": True},
        )
        db.one(
            "UPDATE sandbox_jobs SET plan=%s WHERE id=%s RETURNING id",
            (jsonb({"explanation": "changed", "steps": []}), job),
        )
    worker.tick()
    assert len(runner.calls) == 1
    assert client.get("/api/sandbox/jobs/" + job).json()["status"] in (
        "denied",
        "cancelled",
        "uncertain",
    )


def test_browser_failed_write_is_uncertain_and_not_retried(sandbox):
    client, _, _, _, runner, worker, _ = sandbox
    job, row = browser_ready(sandbox)
    client.post(
        f"/api/sandbox/jobs/{job}/decision",
        json={"digest": row["approval_digest"], "approve": True},
    )
    runner.fail = True
    worker.tick()
    assert client.get("/api/sandbox/jobs/" + job).json()["status"] == "uncertain"
    assert not worker.tick()
    assert len(runner.calls) == 2


def test_owner_scope_csrf_and_admission_limits(sandbox, settings):
    client, _, _, db, _, _, project = sandbox
    assert (
        client.post(
            "/api/sandbox/jobs",
            headers={"X-CSRF-Token": "wrong"},
            json={"kind": "code", "goal": "hello", "project_id": project},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/sandbox/jobs",
            json={"kind": "code", "goal": "hello", "project_id": str(uuid.uuid4())},
        ).status_code
        == 404
    )
    assert client.get("/api/sandbox/jobs/" + str(uuid.uuid4())).status_code == 404
    assert (
        client.post(
            "/api/sandbox/jobs",
            json={
                "kind": "browser",
                "goal": "hello",
                "project_id": project,
                "url": "https://169.254.169.254/",
            },
        ).status_code
        == 422
    )
    settings.max_daily_runs = 1
    enqueue(sandbox)
    assert (
        client.post(
            "/api/sandbox/jobs", json={"kind": "code", "goal": "hello", "project_id": project}
        ).status_code
        == 429
    )
    assert db.one("SELECT count(*) AS n FROM sandbox_jobs")["n"] == 1
    assert not client.get("/api/sandbox/status").json()["worker_online"]


def test_crash_recovery_never_replays_effects(sandbox):
    client, _, _, db, runner, worker, _ = sandbox
    job = enqueue(sandbox)
    claimed = worker.claim()
    db.one(
        "UPDATE sandbox_jobs SET lease_until=now()-interval '1 second' WHERE id=%s RETURNING id",
        (job,),
    )
    assert worker.claim() is None
    assert client.get("/api/sandbox/jobs/" + job).json()["status"] == "failed"
    assert worker.cancelled(claimed)
    assert not runner.calls


def test_malformed_plan_does_not_dispatch(sandbox):
    client, vendor, _, _, runner, worker, _ = sandbox
    vendor.completions.append({"content": "not json"})
    job = enqueue(sandbox)
    worker.tick()
    assert client.get("/api/sandbox/jobs/" + job).json()["status"] == "failed"
    assert not runner.calls
