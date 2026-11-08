import hashlib
import secrets
from datetime import datetime, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from commander.errors import DomainError

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def throttle(db, key, limit=10):
    row = db.one(
        """INSERT INTO rate_limits(key,count) VALUES (%s,1)
      ON CONFLICT(key) DO UPDATE SET count=CASE WHEN rate_limits.window_at<now()-interval '1 minute' THEN 1 ELSE rate_limits.count+1 END,
      window_at=CASE WHEN rate_limits.window_at<now()-interval '1 minute' THEN now() ELSE rate_limits.window_at END RETURNING count""",
        (key,),
    )
    if row["count"] > limit:
        raise DomainError("Too many requests. Try again in one minute.", 429, "rate_limited")


def bootstrap(db, settings, data):
    if not secrets.compare_digest(data.token, settings.bootstrap_token):
        raise DomainError("Invalid bootstrap token", 403)
    with db.connect() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(714894)")
        if conn.execute("SELECT 1 FROM owners LIMIT 1").fetchone():
            raise DomainError("Owner already exists. Sign in.", 409)
        owner = conn.execute(
            "INSERT INTO owners(username,password_hash,role) VALUES (%s,%s,'operator') RETURNING id,username",
            (data.username, hasher.hash(data.password)),
        ).fetchone()
    return owner


def login(db, data):
    owner = db.one("SELECT * FROM owners WHERE username=%s", (data.username,))
    try:
        hasher.verify(owner["password_hash"] if owner else DUMMY_HASH, data.password)
    except (VerificationError, InvalidHashError):
        raise DomainError("Invalid username or password", 401, "invalid_credentials") from None
    if not owner or owner["disabled_at"]:
        raise DomainError("Invalid username or password", 401, "invalid_credentials")
    return owner


def insert_session(conn, owner):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO auth_sessions(token_hash,owner_id,csrf,expires_at,reauthenticated_at) VALUES (%s,%s,%s,now()+interval '12 hours',now())",
        (digest(token), owner["id"], csrf),
    )
    return token, {"owner_id": str(owner["id"]), "username": owner["username"], "csrf": csrf}


def session(db, owner):
    with db.connect() as conn:
        # Serialize session issuance against disabling the account.
        active = conn.execute(
            "SELECT id,username FROM owners WHERE id=%s AND disabled_at IS NULL FOR UPDATE",
            (owner["id"],),
        ).fetchone()
        if not active:
            raise DomainError("Sign in to continue", 401, "unauthenticated")
        return insert_session(conn, active)


def require_active(db, owner):
    row = db.one("SELECT id,role FROM owners WHERE id=%s AND disabled_at IS NULL", (owner,))
    if not row:
        raise DomainError("Sign in to continue", 401, "unauthenticated")
    return row


def require_operator(db, owner):
    row = require_active(db, owner)
    if row["role"] != "operator":
        raise DomainError("Operator access required", 403, "operator_required")
    return row


def verify_password(password_hash, password):
    try:
        hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        raise DomainError("Password verification failed", 401, "invalid_credentials") from None


def authenticate(db, request):
    token = request.cookies.get("commander_session", "")
    row = db.one(
        "SELECT s.*,o.username FROM auth_sessions s JOIN owners o ON o.id=s.owner_id WHERE token_hash=%s AND o.disabled_at IS NULL",
        (digest(token),),
    )
    if not row or row["expires_at"] <= datetime.now(timezone.utc):
        raise DomainError("Sign in to continue", 401, "unauthenticated")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), row["csrf"]):
            raise DomainError("Refresh the page and try again", 403, "csrf")
    return row


def list_sessions(db, owner, token):
    return db.all(
        """SELECT session_id AS id,created_at,expires_at,reauthenticated_at,
          (token_hash=%s) AS current FROM auth_sessions
          WHERE owner_id=%s AND expires_at>now() ORDER BY created_at DESC,session_id""",
        (digest(token), owner),
    )


def revoke_session(db, owner, session_id):
    with db.connect() as conn:
        row = conn.execute(
            "DELETE FROM auth_sessions WHERE owner_id=%s AND session_id=%s RETURNING session_id",
            (owner, session_id),
        ).fetchone()
        if not row:
            raise DomainError("Session not found", 404)
        conn.execute(
            "INSERT INTO auth_events(owner_id,session_id,kind) VALUES (%s,%s,'session_revoked')",
            (owner, session_id),
        )


def reauthenticate(db, owner, token, password):
    throttle(db, "reauth:" + str(owner), 5)
    # Bind validation/update to this still-active session, including concurrent
    # revocation. A password check cannot recreate a revoked session.
    with db.connect() as conn:
        row = conn.execute(
            """SELECT s.session_id,o.password_hash FROM auth_sessions s JOIN owners o ON o.id=s.owner_id
              WHERE s.owner_id=%s AND s.token_hash=%s AND s.expires_at>now() AND o.disabled_at IS NULL FOR UPDATE OF s""",
            (owner, digest(token)),
        ).fetchone()
        if not row:
            raise DomainError("Sign in to continue", 401, "unauthenticated")
        verify_password(row["password_hash"], password)
        conn.execute(
            "UPDATE auth_sessions SET reauthenticated_at=now() WHERE session_id=%s",
            (row["session_id"],),
        )
        conn.execute(
            "INSERT INTO auth_events(owner_id,session_id,kind) VALUES (%s,%s,'reauthenticated')",
            (owner, row["session_id"]),
        )


def require_recent(db, owner, token):
    require_active(db, owner)
    row = db.one(
        """SELECT session_id FROM auth_sessions WHERE owner_id=%s AND token_hash=%s
          AND expires_at>now() AND reauthenticated_at>now()-interval '5 minutes'""",
        (owner, digest(token)),
    )
    if not row:
        raise DomainError(
            "Verify your password again before changing authority", 403, "reauthentication_required"
        )
    return row["session_id"]
