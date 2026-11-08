"""Session revocation and recent reauthentication never confer cross-owner authority."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_workflows import app as workflow_app

from commander import auth
from commander.errors import DomainError

app = workflow_app


def test_session_list_redacts_tokens_and_revokes_only_owned_session(app):
    client, _, owner, db = app
    second = TestClient(client.app)
    login = second.post(
        "/api/auth/login", json={"username": "owner", "password": "fictional-test-password"}
    )
    assert login.status_code == 200, login.text
    sessions = client.get("/api/auth/sessions")
    assert sessions.status_code == 200
    rows = sessions.json()
    assert len(rows) == 2 and sum(item["current"] for item in rows) == 1
    assert all(
        set(item) == {"id", "created_at", "expires_at", "reauthenticated_at", "current"}
        for item in rows
    )
    target = next(row["id"] for row in rows if not row["current"])
    foreign = db.one(
        "INSERT INTO owners(username,password_hash) VALUES ('foreign-session','not-a-login-hash') RETURNING id"
    )
    foreign_token, _ = auth.session(db, {**foreign, "username": "foreign-session"})
    foreign_id = db.one(
        "SELECT session_id FROM auth_sessions WHERE token_hash=%s", (auth.digest(foreign_token),)
    )["session_id"]
    assert client.delete("/api/auth/sessions/" + str(foreign_id)).status_code == 404
    assert client.delete("/api/auth/sessions/" + target).status_code == 200
    assert second.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me").status_code == 200
    assert client.delete("/api/auth/sessions/" + str(uuid4())).status_code == 404


def test_reauthentication_is_csrf_bound_rate_limited_and_session_local(app):
    client, _, owner, db = app
    db.one(
        "UPDATE auth_sessions SET reauthenticated_at=NULL WHERE owner_id=%s RETURNING owner_id",
        (owner,),
    )
    response = client.post("/api/auth/reauthenticate", json={"password": "wrong-credential"})
    assert response.status_code == 401 and "wrong-credential" not in response.text
    assert (
        db.one("SELECT reauthenticated_at FROM auth_sessions WHERE owner_id=%s", (owner,))[
            "reauthenticated_at"
        ]
        is None
    )
    response = client.post(
        "/api/auth/reauthenticate",
        json={"password": "fictional-test-password"},
        headers={"X-CSRF-Token": "wrong"},
    )
    assert response.status_code == 403
    assert (
        client.post(
            "/api/auth/reauthenticate", json={"password": "fictional-test-password"}
        ).status_code
        == 200
    )
    token = client.cookies.get("commander_session")
    auth.require_recent(db, owner, token)
    auth.session(db, {"id": owner, "username": "owner"})
    db.one(
        "UPDATE auth_sessions SET reauthenticated_at=now()-interval '6 minutes' WHERE token_hash=%s RETURNING owner_id",
        (auth.digest(token),),
    )
    with pytest.raises(DomainError) as failure:
        auth.require_recent(db, owner, token)
    assert failure.value.code == "reauthentication_required"
    for _ in range(4):
        client.post("/api/auth/reauthenticate", json={"password": "wrong-credential"})
    assert (
        client.post(
            "/api/auth/reauthenticate", json={"password": "fictional-test-password"}
        ).status_code
        == 429
    )


def test_current_session_revocation_and_expired_session_listing(app):
    client, _, owner, db = app
    rows = client.get("/api/auth/sessions")
    assert rows.status_code == 200
    current = next(item["id"] for item in rows.json() if item["current"])
    expired, _ = auth.session(db, {"id": owner, "username": "owner"})
    db.one(
        "UPDATE auth_sessions SET expires_at=now()-interval '1 second' WHERE token_hash=%s RETURNING owner_id",
        (auth.digest(expired),),
    )
    assert len(client.get("/api/auth/sessions").json()) == 1
    assert client.delete("/api/auth/sessions/" + current).status_code == 200
    assert client.get("/api/auth/me").status_code == 401
