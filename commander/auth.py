import hashlib
import secrets
from datetime import datetime, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

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
            "INSERT INTO owners(username,password_hash) VALUES (%s,%s) RETURNING id,username",
            (data.username, hasher.hash(data.password)),
        ).fetchone()
    return owner


def login(db, data):
    owner = db.one("SELECT * FROM owners WHERE username=%s", (data.username,))
    try:
        hasher.verify(owner["password_hash"] if owner else DUMMY_HASH, data.password)
    except VerificationError:
        raise DomainError("Invalid username or password", 401, "invalid_credentials") from None
    if not owner:
        raise DomainError("Invalid username or password", 401)
    return owner


def session(db, owner):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.one(
        "INSERT INTO auth_sessions(token_hash,owner_id,csrf,expires_at) VALUES (%s,%s,%s,now()+interval '12 hours') RETURNING owner_id",
        (digest(token), owner["id"], csrf),
    )
    return token, {"owner_id": str(owner["id"]), "username": owner["username"], "csrf": csrf}


def authenticate(db, request):
    token = request.cookies.get("commander_session", "")
    row = db.one(
        "SELECT s.*,o.username FROM auth_sessions s JOIN owners o ON o.id=s.owner_id WHERE token_hash=%s",
        (digest(token),),
    )
    if not row or row["expires_at"] <= datetime.now(timezone.utc):
        raise DomainError("Sign in to continue", 401, "unauthenticated")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), row["csrf"]):
            raise DomainError("Refresh the page and try again", 403, "csrf")
    return row
