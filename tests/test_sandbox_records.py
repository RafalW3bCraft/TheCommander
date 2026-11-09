"""Real PostgreSQL ownership, cancellation evidence and runner admission regressions."""

import base64
import io
import tarfile

import pytest
from test_sandbox_workflows import sandbox as sandbox_fixture
from test_workflows import app as workflow_app

from commander.errors import DomainError
from commander.sandbox.artifacts import read_archive

app = workflow_app
sandbox = sandbox_fixture


def archive(entries):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as tar:
        for name, data, kind in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            if kind == tarfile.SYMTYPE:
                info.linkname = "/etc/passwd"
            else:
                info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    output.seek(0)
    return output


def test_artifact_archive_accepts_only_bounded_regular_output():
    result = read_archive(archive([("output/result.csv", b"value\n42\n", tarfile.REGTYPE)]))
    assert result[0]["name"] == "result.csv"
    assert base64.b64decode(result[0]["data"]) == b"value\n42\n"
    for entries in [
        [("output/link.txt", b"", tarfile.SYMTYPE)],
        [("output/../../secret.txt", b"secret", tarfile.REGTYPE)],
        [("output/a.exe", b"bad", tarfile.REGTYPE)],
        [("output/huge.txt", b"x" * (1024 * 1024 + 1), tarfile.REGTYPE)],
        [(f"output/{i}.txt", b"x", tarfile.REGTYPE) for i in range(6)],
    ]:
        with pytest.raises(DomainError, match="artifact"):
            read_archive(archive(entries))


def test_offline_runner_rejects_admission_and_readiness(sandbox):
    client, _, _, db, _, _, project = sandbox
    db.one("DELETE FROM sandbox_heartbeats WHERE id='runner' RETURNING id")
    response = client.post(
        "/api/sandbox/jobs", json={"kind": "code", "goal": "Compute 42", "project_id": project}
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "worker_unavailable"
    assert client.get("/health/ready").status_code == 503


def test_cancelled_execution_keeps_receipt_and_private_artifact(sandbox):
    client, _, owner, db, runner, worker, project = sandbox
    db.one(
        "INSERT INTO sandbox_heartbeats(id) VALUES('runner') ON CONFLICT(id) DO UPDATE SET seen_at=now() RETURNING id"
    )
    created = client.post(
        "/api/sandbox/jobs", json={"kind": "code", "goal": "Compute 42", "project_id": project}
    ).json()
    job = worker.claim()
    assert str(job["id"]) == created["id"]
    old_execute = runner.execute

    def execute(*args, **kwargs):
        result = old_execute(*args, **kwargs)
        client.post(f"/api/sandbox/jobs/{job['id']}/cancel")
        return {
            **result,
            "artifacts": [{"name": "answer.txt", "data": base64.b64encode(b"42").decode()}],
        }

    runner.execute = execute
    with pytest.raises(DomainError, match="cancelled"):
        worker.run_container(job, "code", "print(42)")
    saved = client.get(f"/api/sandbox/jobs/{job['id']}").json()
    assert saved["status"] == "cancelled"
    assert saved["receipt"]["destroyed"] is True
    attempt = db.one("SELECT * FROM sandbox_attempts WHERE job_id=%s", (job["id"],))
    assert attempt["finished_at"] and attempt["receipt"]["destroyed"]
    files = client.get(f"/api/sandbox/jobs/{job['id']}/artifacts").json()
    assert len(files) == 1
    download = client.get(files[0]["download_url"])
    assert download.content == b"42"
    assert download.headers["content-disposition"].startswith("attachment;")
    assert download.headers["x-content-type-options"] == "nosniff"
    # Access is derived from the principal and persisted job, never client input.
    db.one("UPDATE sandbox_jobs SET owner_id=owner_id WHERE id=%s RETURNING id", (job["id"],))
    from fastapi.testclient import TestClient

    anonymous = TestClient(client.app)
    assert anonymous.get(files[0]["download_url"]).status_code == 401


def test_claim_serializes_global_execution(sandbox):
    client, _, _, db, _, worker, project = sandbox
    db.one(
        "INSERT INTO sandbox_heartbeats(id) VALUES('runner') ON CONFLICT(id) DO UPDATE SET seen_at=now() RETURNING id"
    )
    for _ in range(2):
        assert (
            client.post(
                "/api/sandbox/jobs",
                json={"kind": "code", "goal": "Compute 42", "project_id": project},
            ).status_code
            == 201
        )
    assert worker.claim()
    assert worker.claim() is None


def test_artifact_scope_deletion_and_retention_keep_receipts(sandbox):
    from fastapi.testclient import TestClient
    from test_accounts import invitation, personal_client

    from commander.db import json
    from commander.sandbox.retention import purge

    client, _, _, db, runner, worker, project = sandbox
    created = client.post(
        "/api/sandbox/jobs", json={"kind": "code", "goal": "Compute 42", "project_id": project}
    ).json()
    job = worker.claim()
    old_execute = runner.execute

    def execute(*args, **kwargs):
        result = old_execute(*args, **kwargs)
        return {
            **result,
            "artifacts": [{"name": "answer.txt", "data": base64.b64encode(b"42").decode()}],
        }

    runner.execute = execute
    observed = worker.run_container(job, "code", "print(42)")
    assert "data" not in observed["artifacts"][0]
    files = client.get(f"/api/sandbox/jobs/{created['id']}/artifacts").json()
    other, _ = personal_client(client, invitation(client)["token"], "isolated-artifact-user")
    assert other.get(files[0]["download_url"]).status_code == 404
    assert other.delete(files[0]["download_url"]).status_code == 404
    without_csrf = TestClient(client.app)
    without_csrf.cookies.update(client.cookies)
    assert without_csrf.delete(files[0]["download_url"]).status_code == 403
    assert client.delete(f"/api/sandbox/jobs/{created['id']}/evidence").status_code == 409
    db.one(
        "UPDATE sandbox_jobs SET status='succeeded',evidence=%s,approval_snapshot=%s,updated_at=now()-interval '8 days' WHERE id=%s RETURNING id",
        (
            json({"screenshot": "fixture-only-base64", "screenshot_sha256": "a" * 64}),
            json({"screenshot": "fixture-preview"}),
            job["id"],
        ),
    )
    db.one(
        "UPDATE sandbox_artifacts SET created_at=now()-interval '8 days' WHERE job_id=%s RETURNING id",
        (job["id"],),
    )
    assert purge(db, 7) == {"artifacts_removed": 1, "screenshots_removed": 1}
    assert client.get(files[0]["download_url"]).status_code == 404
    saved = client.get(f"/api/sandbox/jobs/{job['id']}").json()
    assert "screenshot" not in saved["evidence"] and "screenshot" not in saved["approval_snapshot"]
    assert saved["receipt"]["destroyed"]
    tombstone = db.one(
        "SELECT deleted_at,data,sha256 FROM sandbox_artifacts WHERE job_id=%s", (job["id"],)
    )
    assert tombstone["deleted_at"] and tombstone["data"] is None and tombstone["sha256"]


def test_chat_and_sandbox_share_daily_admission(sandbox):
    client, _, _, db, _, _, project = sandbox
    db.settings.max_daily_runs = 1
    assert (
        client.post(
            "/api/sandbox/jobs", json={"kind": "code", "goal": "Compute 42", "project_id": project}
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/runs",
            json={
                "skill": "conversation",
                "prompt": "A controlled test task",
                "project_id": project,
            },
        ).status_code
        == 429
    )
