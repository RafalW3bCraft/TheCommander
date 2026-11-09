"""Invitation-only private accounts; server credentials remain operator-owned."""

import secrets
from datetime import datetime
from typing import Literal
from uuid import UUID

import psycopg
from fastapi import Depends, Request, Response
from pydantic import BaseModel, Field, field_validator

from commander import auth
from commander.connections import owner_lock
from commander.contracts import Login, StatusView, Strict, UserView
from commander.errors import DomainError


class Registration(Login):
    invitation: str = Field(min_length=32, max_length=200)

    @field_validator("username")
    @classmethod
    def username_not_blank(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Enter a username")
        return value


class ProfileEdit(Strict):
    display_name: str = Field(max_length=120)


class PasswordChange(Strict):
    current_password: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=12, max_length=256)


class SessionRevocation(Strict):
    scope: Literal["other", "all"] = "other"


class InvitationInput(Strict):
    purpose: Literal["personal", "judge"] = "personal"
    expires_hours: int = Field(default=24, ge=1, le=168)


class ProfileView(BaseModel):
    owner_id: UUID
    username: str
    display_name: str
    role: Literal["operator", "personal"]
    disabled_at: datetime | None
    workspace_id: UUID
    created_at: datetime


class InvitationView(BaseModel):
    id: UUID
    purpose: Literal["personal", "judge"]
    expires_at: datetime
    consumed_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class InvitationCreated(InvitationView):
    token: str


def profile(db, owner):
    row = db.one(
        """SELECT o.id AS owner_id,o.username,o.display_name,o.role,o.disabled_at,o.created_at,
         w.id AS workspace_id FROM owners o JOIN workspaces w ON w.owner_id=o.id WHERE o.id=%s""",
        (owner,),
    )
    if not row:
        raise DomainError("Account not found", 404)
    return row


def register(db, data):
    # Hash work is bounded by the route throttle. Only the digest is persisted;
    # FOR UPDATE makes token consumption atomic across registration attempts.
    password_hash = auth.hasher.hash(data.password)
    try:
        with db.connect() as conn:
            invitation = conn.execute(
                """SELECT id FROM account_invitations WHERE token_hash=%s AND consumed_at IS NULL
                 AND revoked_at IS NULL AND expires_at>now() FOR UPDATE""",
                (auth.digest(data.invitation),),
            ).fetchone()
            if not invitation:
                raise DomainError("Invitation is invalid or unavailable", 403, "invalid_invitation")
            owner = conn.execute(
                "INSERT INTO owners(username,password_hash,role) VALUES (%s,%s,'personal') RETURNING id,username",
                (data.username, password_hash),
            ).fetchone()
            conn.execute(
                "UPDATE account_invitations SET consumed_at=now(),consumed_by=%s WHERE id=%s",
                (owner["id"], invitation["id"]),
            )
            conn.execute(
                "INSERT INTO account_events(actor_id,subject_id,kind) VALUES (%s,%s,'registered')",
                (owner["id"], owner["id"]),
            )
            return owner
    except psycopg.errors.UniqueViolation:
        raise DomainError(
            "Account could not be registered with these details", 409, "registration_conflict"
        ) from None


def create_invitation(db, operator, data):
    auth.require_operator(db, operator)
    token = secrets.token_urlsafe(32)
    with owner_lock(db, operator):
        auth.require_operator(db, operator)
        with db.connect() as conn:
            row = conn.execute(
                """INSERT INTO account_invitations(token_hash,created_by,purpose,expires_at)
                 VALUES (%s,%s,%s,now()+(%s * interval '1 hour'))
                 RETURNING id,purpose,expires_at,consumed_at,revoked_at,created_at""",
                (auth.digest(token), operator, data.purpose, data.expires_hours),
            ).fetchone()
            conn.execute(
                "INSERT INTO account_events(actor_id,kind) VALUES (%s,'invitation_created')",
                (operator,),
            )
    return {**row, "token": token}


def revoke_invitation(db, operator, invitation):
    with owner_lock(db, operator):
        auth.require_operator(db, operator)
        with db.connect() as conn:
            row = conn.execute(
                "UPDATE account_invitations SET revoked_at=now() WHERE id=%s RETURNING id",
                (invitation,),
            ).fetchone()
            if not row:
                raise DomainError("Invitation not found", 404)
            conn.execute(
                "INSERT INTO account_events(actor_id,kind) VALUES (%s,'invitation_revoked')",
                (operator,),
            )


def change_password(db, owner, token, data):
    auth.throttle(db, "password:" + str(owner), 5)
    with owner_lock(db, owner):
        auth.require_active(db, owner)
        with db.connect() as conn:
            row = conn.execute(
                """SELECT o.id,o.username,o.password_hash,s.session_id FROM owners o
                 JOIN auth_sessions s ON s.owner_id=o.id WHERE o.id=%s AND s.token_hash=%s
                 AND s.expires_at>now() AND o.disabled_at IS NULL FOR UPDATE OF o,s""",
                (owner, auth.digest(token)),
            ).fetchone()
            if not row:
                raise DomainError("Sign in to continue", 401, "unauthenticated")
            auth.verify_password(row["password_hash"], data.current_password)
            conn.execute(
                "UPDATE owners SET password_hash=%s WHERE id=%s",
                (auth.hasher.hash(data.password), owner),
            )
            conn.execute("DELETE FROM auth_sessions WHERE owner_id=%s", (owner,))
            new_token, result = auth.insert_session(conn, row)
            conn.execute(
                "INSERT INTO account_events(actor_id,subject_id,kind) VALUES (%s,%s,'password_changed')",
                (owner, owner),
            )
    return new_token, result


def revoke_sessions(db, owner, token, scope):
    with owner_lock(db, owner):
        auth.require_active(db, owner)
        with db.connect() as conn:
            conn.execute(
                "DELETE FROM auth_sessions WHERE owner_id=%s AND (%s='all' OR token_hash<>%s)",
                (owner, scope, auth.digest(token)),
            )
            conn.execute(
                "INSERT INTO account_events(actor_id,subject_id,kind) VALUES (%s,%s,'sessions_revoked')",
                (owner, owner),
            )


def disable(db, operator, owner):
    # Same owner lock as connection revoke / provider and action dispatch. This
    # waits for an in-flight authorized operation, then closes future boundaries.
    with owner_lock(db, owner):
        with db.connect() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(714895)")
            actor = conn.execute(
                "SELECT role,disabled_at FROM owners WHERE id=%s", (operator,)
            ).fetchone()
            if not actor or actor["role"] != "operator" or actor["disabled_at"]:
                raise DomainError("Operator access required", 403, "operator_required")
            target = conn.execute(
                "SELECT role FROM owners WHERE id=%s FOR UPDATE", (owner,)
            ).fetchone()
            if not target:
                raise DomainError("Account not found", 404)
            if (
                target["role"] == "operator"
                and not conn.execute(
                    "SELECT 1 FROM owners WHERE role='operator' AND disabled_at IS NULL AND id<>%s LIMIT 1",
                    (owner,),
                ).fetchone()
            ):
                raise DomainError(
                    "The last active operator cannot be disabled", 409, "last_operator"
                )
            conn.execute("UPDATE owners SET disabled_at=now() WHERE id=%s", (owner,))
            conn.execute("DELETE FROM auth_sessions WHERE owner_id=%s", (owner,))
            conn.execute(
                "UPDATE schedules SET paused=true,revision=revision+1 WHERE owner_id=%s", (owner,)
            )
            conn.execute(
                "UPDATE runs SET status='cancelled',error='Account disabled',updated_at=now(),lease_token=NULL,lease_until=NULL WHERE owner_id=%s AND status IN ('queued','running','waiting_approval')",
                (owner,),
            )
            conn.execute(
                "UPDATE actions SET status='denied',error='Account disabled' WHERE owner_id=%s AND status IN ('pending','approved')",
                (owner,),
            )
            conn.execute(
                "UPDATE sandbox_jobs SET status='cancelled',error='Account disabled',updated_at=now(),lease_token=NULL,lease_until=NULL WHERE owner_id=%s AND status IN ('queued','running','waiting_approval','approved')",
                (owner,),
            )
            conn.execute(
                "UPDATE account_invitations SET revoked_at=now() WHERE created_by=%s AND consumed_at IS NULL",
                (owner,),
            )
            conn.execute(
                "INSERT INTO account_events(actor_id,subject_id,kind) VALUES (%s,%s,'account_disabled')",
                (operator, owner),
            )


def register_routes(app, db, settings, principal, logged_in, set_session_cookie):
    def operator(request: Request, owner=Depends(principal)):
        auth.require_operator(db, owner)
        auth.require_recent(db, owner, request.cookies.get("commander_session", ""))
        return owner

    from commander.demo_grants import install_routes

    install_routes(app, db, operator)

    @app.post("/api/auth/register", response_model=UserView)
    def register_account(data: Registration, request: Request, response: Response):
        auth.throttle(db, "register:" + (request.client.host if request.client else "unknown"), 5)
        return logged_in(response, register(db, data))

    @app.get("/api/account", response_model=ProfileView)
    def get_profile(owner=Depends(principal)):
        return profile(db, owner)

    @app.patch("/api/account", response_model=ProfileView)
    def update_profile(data: ProfileEdit, owner=Depends(principal)):
        with owner_lock(db, owner):
            auth.require_active(db, owner)
            with db.connect() as conn:
                conn.execute(
                    "UPDATE owners SET display_name=%s WHERE id=%s",
                    (data.display_name.strip(), owner),
                )
                conn.execute(
                    "INSERT INTO account_events(actor_id,subject_id,kind) VALUES (%s,%s,'profile_updated')",
                    (owner, owner),
                )
        return profile(db, owner)

    @app.post("/api/account/password", response_model=UserView)
    def password(
        data: PasswordChange, request: Request, response: Response, owner=Depends(principal)
    ):
        token, result = change_password(
            db, owner, request.cookies.get("commander_session", ""), data
        )
        set_session_cookie(response, token)
        return result

    @app.post("/api/auth/sessions/revoke", response_model=StatusView)
    def bulk_revoke(
        data: SessionRevocation, request: Request, response: Response, owner=Depends(principal)
    ):
        revoke_sessions(db, owner, request.cookies.get("commander_session", ""), data.scope)
        if data.scope == "all":
            response.delete_cookie("commander_session", path="/")
        return {"status": "revoked"}

    @app.get("/api/admin/invitations", response_model=list[InvitationView])
    def invitations(owner=Depends(operator)):
        return db.all(
            "SELECT id,purpose,expires_at,consumed_at,revoked_at,created_at FROM account_invitations ORDER BY created_at DESC LIMIT 200"
        )

    @app.post("/api/admin/invitations", response_model=InvitationCreated)
    def invite(data: InvitationInput, owner=Depends(operator)):
        return create_invitation(db, owner, data)

    @app.delete("/api/admin/invitations/{invitation_id}", response_model=StatusView)
    def revoke(invitation_id: UUID, owner=Depends(operator)):
        revoke_invitation(db, owner, invitation_id)
        return {"status": "revoked"}

    @app.get("/api/admin/accounts", response_model=list[ProfileView])
    def list_accounts(owner=Depends(operator)):
        return db.all(
            "SELECT o.id AS owner_id,o.username,o.display_name,o.role,o.disabled_at,o.created_at,w.id AS workspace_id FROM owners o JOIN workspaces w ON w.owner_id=o.id ORDER BY o.created_at,o.id LIMIT 200"
        )

    @app.post("/api/admin/accounts/{account_id}/disable", response_model=StatusView)
    def disable_account(account_id: UUID, owner=Depends(operator)):
        disable(db, owner, account_id)
        return {"status": "disabled"}
