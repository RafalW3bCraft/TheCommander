"""Private invitation accounts retain owner scope and never inherit server secrets."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import psycopg
import pytest
from fastapi.testclient import TestClient
from test_workflows import app as workflow_app

from commander import accounts, auth
from commander.connections import Connections
from commander.errors import DomainError

app = workflow_app
PASSWORD = "fictional-personal-password"


def invitation(client, purpose="personal"):
    response = client.post("/api/admin/invitations", json={"purpose": purpose, "expires_hours": 24})
    assert response.status_code == 200, response.text
    return response.json()


def register(client, token, username="personal"):
    return client.post(
        "/api/auth/register", json={"username": username, "password": PASSWORD, "invitation": token}
    )


def personal_client(client, token, username="personal"):
    other = TestClient(client.app)
    response = register(other, token, username)
    assert response.status_code == 200, response.text
    other.headers["X-CSRF-Token"] = response.json()["csrf"]
    return other, response.json()["owner_id"]


def test_invitation_registration_creates_private_workspace_without_authority(app):
    client, _, owner, db = app
    invite = invitation(client)
    other, other_id = personal_client(client, invite["token"])
    profile = other.get("/api/account").json()
    assert profile["role"] == "personal" and profile["owner_id"] == other_id
    assert profile["workspace_id"] != client.get("/api/account").json()["workspace_id"]
    project = db.one("SELECT * FROM projects WHERE owner_id=%s", (other_id,))
    assert str(project["workspace_id"]) == profile["workspace_id"]
    assert other.get("/api/connections").status_code == 200
    assert not db.all("SELECT * FROM connections WHERE owner_id=%s", (other_id,))
    assert other.post("/api/connections/import-environment").status_code == 403
    with pytest.raises(DomainError) as error:
        Connections(db, db.settings).import_environment(other_id)
    assert error.value.status == 403
    assert other.get("/api/admin/accounts").status_code == 403
    assert other.post("/api/admin/invitations", json={}).status_code == 403
    assert not db.one("SELECT 1 FROM connections WHERE owner_id=%s", (other_id,))
    assert db.one("SELECT role FROM owners WHERE id=%s", (owner,))["role"] == "operator"
    assert "token" not in client.get("/api/admin/invitations").text


def test_invalid_used_expired_revoked_invitations_and_generic_duplicate(app):
    client, _, owner, db = app
    newcomer = TestClient(client.app)
    assert register(newcomer, "a" * 43).status_code == 403
    invite = invitation(client)
    assert register(newcomer, invite["token"]).status_code == 200
    assert register(newcomer, invite["token"], "replay").status_code == 403
    duplicate = invitation(client)
    response = register(newcomer, duplicate["token"])
    assert response.status_code == 409
    assert not db.one("SELECT consumed_at FROM account_invitations WHERE id=%s", (duplicate["id"],))["consumed_at"]
    assert register(newcomer, duplicate["token"], "another").status_code == 200
    expired = invitation(client)
    db.one("UPDATE account_invitations SET expires_at=now()-interval '1 second' WHERE id=%s RETURNING id", (expired["id"],))
    assert register(newcomer, expired["token"], "expired").status_code == 403
    revoked = invitation(client, "judge")
    assert client.delete("/api/admin/invitations/" + revoked["id"]).status_code == 200
    assert register(newcomer, revoked["token"], "revoked").status_code == 403
    assert client.get("/api/auth/status").json()["bootstrap_required"] is False


def test_atomic_invitation_consumption_and_duplicate_registration_race(app):
    client, _, owner, db = app
    invite = invitation(client)
    def consume(username):
        try:
            return accounts.register(db, SimpleNamespace(username=username, password=PASSWORD, invitation=invite["token"]))
        except DomainError as exc:
            return exc.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(consume, ("racer-one", "racer-two")))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert 403 in results
    first, second = invitation(client), invitation(client)
    def duplicate(token):
        try:
            return accounts.register(db, SimpleNamespace(username="duplicate", password=PASSWORD, invitation=token))
        except DomainError as exc:
            return exc.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(duplicate, (first["token"], second["token"])))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert 409 in results


def test_password_rotation_profile_and_session_bulk_revocation(app):
    client, _, owner, db = app
    other, other_id = personal_client(client, invitation(client)["token"])
    second = TestClient(client.app)
    login = second.post("/api/auth/login", json={"username": "personal", "password": PASSWORD})
    assert login.status_code == 200
    second.headers["X-CSRF-Token"] = login.json()["csrf"]
    old_csrf, old_cookie = other.headers["X-CSRF-Token"], other.cookies.get("commander_session")
    assert other.patch("/api/account", json={"display_name": "Personal user"}).json()["display_name"] == "Personal user"
    assert other.patch("/api/account", json={"role": "operator"}).status_code == 422
    assert other.post("/api/account/password", json={"current_password": "incorrect-password", "password": "new-fictional-password"}).status_code == 401
    changed = other.post("/api/account/password", json={"current_password": PASSWORD, "password": "new-fictional-password"})
    assert changed.status_code == 200, changed.text
    assert changed.json()["csrf"] != old_csrf
    assert other.cookies.get("commander_session") != old_cookie
    assert second.get("/api/auth/me").status_code == 401
    assert other.patch("/api/account", json={"display_name": "Blocked"}).status_code == 403
    other.headers["X-CSRF-Token"] = changed.json()["csrf"]
    assert other.post("/api/auth/sessions/revoke", json={"scope": "other"}).status_code == 200
    assert other.get("/api/auth/me").status_code == 200
    assert other.post("/api/auth/sessions/revoke", json={"scope": "all"}).status_code == 200
    assert other.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me").status_code == 200


def test_operator_recent_auth_disable_and_no_last_operator_disable(app):
    client, _, owner, db = app
    other, other_id = personal_client(client, invitation(client)["token"])
    db.one("UPDATE auth_sessions SET reauthenticated_at=now()-interval '6 minutes' WHERE owner_id=%s RETURNING owner_id", (owner,))
    assert client.post("/api/admin/invitations", json={}).status_code == 403
    assert client.post("/api/admin/accounts/" + other_id + "/disable").status_code == 403
    assert client.post("/api/auth/reauthenticate", json={"password": "fictional-test-password"}).status_code == 200
    assert client.post("/api/admin/accounts/" + str(owner) + "/disable").status_code == 409
    assert client.post("/api/admin/accounts/" + other_id + "/disable").status_code == 200
    assert other.get("/api/auth/me").status_code == 401
    response = other.post("/api/auth/login", json={"username": "personal", "password": PASSWORD})
    absent = other.post("/api/auth/login", json={"username": "absent", "password": PASSWORD})
    assert response.status_code == absent.status_code == 401
    assert response.json() == absent.json()
    with pytest.raises(DomainError):
        auth.require_active(db, other_id)
    with pytest.raises(DomainError):
        auth.session(db, {"id": other_id, "username": "personal"})


def test_database_blocks_cross_account_usage_workspace_and_memory_index(app):
    client, _, owner, db = app
    _, other_id = personal_client(client, invitation(client)["token"])
    project = db.one("SELECT * FROM projects WHERE owner_id=%s", (owner,))
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        db.one("INSERT INTO projects(owner_id,name,workspace_id) VALUES (%s,'Wrong',%s) RETURNING id", (other_id, project["workspace_id"]))
    run = db.one("INSERT INTO runs(owner_id,skill,skill_version,prompt) VALUES (%s,'chat','1','test') RETURNING id", (owner,))
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        db.one("INSERT INTO usage(owner_id,run_id,model,latency_ms) VALUES (%s,%s,'fixture',1) RETURNING id", (other_id, run["id"]))
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        db.one("INSERT INTO memory_index_jobs(memory_id,owner_id,project_id,revision) VALUES (gen_random_uuid(),%s,%s,1) RETURNING memory_id", (other_id, project["id"]))
