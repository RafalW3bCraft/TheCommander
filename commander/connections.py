from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet

from commander.db import json
from commander.errors import DomainError
from commander.providers import Provider, ProviderError

KINDS = ("nebius", "github", "tavily", "workspace")


def usable_secret(value):
    return bool(
        value and not any(part in value.lower() for part in ("your-", "change-this", "placeholder"))
    )


@contextmanager
def owner_lock(db, owner):
    # Session lock serializes revoke/cancel against the dispatch boundary. Separate
    # transactions persist intent before I/O; process death releases the lock.
    with db.connect() as conn:
        conn.commit()
        conn.autocommit = True
        conn.execute("SELECT pg_advisory_lock(hashtextextended(%s, 719))", (str(owner),))
        try:
            yield
        finally:
            conn.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 719))", (str(owner),))


class Connections:
    def __init__(self, db, settings, transport=None):
        self.db, self.settings = db, settings
        self.cipher = Fernet(settings.encryption_key.encode())
        self.provider = Provider(settings, transport)

    def get(self, owner, kind):
        row = self.db.one("SELECT * FROM connections WHERE owner_id=%s AND kind=%s", (owner, kind))
        if not row or row["status"] == "revoked":
            raise DomainError(f"Configure the {kind} connection first", 409, "disconnected")
        expiry = row["config"].get("expires_at")
        if expiry and datetime.fromisoformat(expiry) <= datetime.now(timezone.utc):
            raise DomainError(f"The {kind} credential has expired; replace it", 409, "expired")
        return row

    def secret(self, row):
        return self.cipher.decrypt(bytes(row["secret"])).decode() if row["secret"] else ""

    def list(self, owner):
        rows = {
            r["kind"]: r
            for r in self.db.all("SELECT * FROM connections WHERE owner_id=%s", (owner,))
        }
        result = []
        for kind in KINDS:
            row = rows.get(kind)
            item: dict[str, Any] = {
                "kind": kind,
                "status": "unconfigured",
                "revision": 0,
                "config": {},
                "validated_at": None,
                "detail": None,
            }
            if row:
                item.update({k: row[k] for k in item if k in row})
                if row["status"] == "validated" and row["validated_at"] < datetime.now(
                    timezone.utc
                ) - timedelta(days=1):
                    item["status"] = "stale"
            if (
                row
                and row["status"] != "revoked"
                and row["config"].get("expires_at")
                and datetime.fromisoformat(row["config"]["expires_at"])
                <= datetime.now(timezone.utc)
            ):
                item["status"] = "expired"
            if kind == "nebius":
                item["config"] = {
                    **item["config"],
                    "model": self.settings.nebius_model,
                    "endpoint": self.settings.nebius_base_url,
                }
            result.append(item)
        return result

    def save(self, owner, kind, data):
        if kind not in KINDS:
            raise DomainError("Unknown connection", 404)
        if kind == "github" and not data.repository:
            raise DomainError("Select exactly one owner/repository", 422)
        current = self.db.one(
            "SELECT * FROM connections WHERE owner_id=%s AND kind=%s", (owner, kind)
        )
        secret = data.secret
        if not secret and current and current["status"] != "revoked":
            secret = self.secret(current)
        if kind != "workspace" and not usable_secret(secret):
            raise DomainError("Enter a real provider credential", 422, "unconfigured")
        config = {
            "repository": data.repository,
            "domains": data.domains,
            "enabled": data.enabled,
            "expires_at": data.expires_at.isoformat() if data.expires_at else None,
        }
        with owner_lock(self.db, owner):
            self.db.one(
                """INSERT INTO connections(owner_id,kind,secret,config) VALUES (%s,%s,%s,%s)
            ON CONFLICT(owner_id,kind) DO UPDATE SET secret=EXCLUDED.secret,config=EXCLUDED.config,status='configured',revision=connections.revision+1,validated_at=NULL,detail=NULL RETURNING kind""",
                (
                    owner,
                    kind,
                    self.cipher.encrypt(secret.encode()) if secret else None,
                    json(config),
                ),
            )
            self.invalidate(owner, kind)
        return self.list(owner)

    def invalidate(self, owner, kind):
        if kind == "github":
            self.db.one(
                "UPDATE actions SET status='denied',error='Connection changed or revoked' WHERE owner_id=%s AND status IN ('pending','approved') RETURNING id",
                (owner,),
            )
            self.db.one(
                "UPDATE runs SET status='failed',error='Connection changed or revoked',updated_at=now() WHERE owner_id=%s AND status='waiting_approval' RETURNING id",
                (owner,),
            )

    def revoke(self, owner, kind):
        with owner_lock(self.db, owner):
            self.db.one(
                "UPDATE connections SET status='revoked',secret=NULL,revision=revision+1,validated_at=NULL WHERE owner_id=%s AND kind=%s RETURNING kind",
                (owner, kind),
            )
            self.invalidate(owner, kind)
        return self.list(owner)

    def validate(self, owner, kind):
        with owner_lock(self.db, owner):
            return self._validate_locked(owner, kind)

    def _validate_locked(self, owner, kind):
        row = self.get(owner, kind)
        status, detail = "validated", "Connection checked successfully"
        try:
            secret = self.secret(row)
            if kind == "nebius":
                models = self.provider.request(
                    "GET", self.settings.nebius_base_url.rstrip("/") + "/models", secret, retry=True
                )
                if self.settings.nebius_model not in [m["id"] for m in models.get("data", [])]:
                    raise ProviderError(
                        "Configured NVIDIA model is unavailable to this account",
                        502,
                        "unavailable_model",
                    )
                from commander.inference import complete

                complete(
                    self.db,
                    self.settings,
                    self.provider,
                    owner,
                    secret,
                    [{"role": "user", "content": "Reply with OK only."}],
                )
                detail = "Model listed and harmless inference completed"
            elif kind == "github":
                self.provider.request(
                    "GET",
                    "https://api.github.com/repos/" + row["config"]["repository"],
                    secret,
                    retry=True,
                )
                detail = "Repository read verified. Issue-write permission is verified only when an approved issue succeeds."
            elif kind == "tavily":
                self.provider.search(
                    secret, "NVIDIA developer documentation", row["config"].get("domains", [])
                )
            else:
                from commander.workspace import Workspace

                Workspace(self.settings.workspace_root, owner).check()
        except DomainError as exc:
            status, detail = exc.code, exc.message
        self.db.one(
            "UPDATE connections SET status=%s,detail=%s,validated_at=now() WHERE owner_id=%s AND kind=%s AND revision=%s RETURNING kind",
            (status, detail, owner, kind, row["revision"]),
        )
        return self.list(owner)

    def import_environment(self, owner):
        from commander.contracts import ConnectionInput

        imported = []
        for kind, key in [
            ("nebius", self.settings.nebius_api_key),
            ("github", self.settings.github_token),
            ("tavily", self.settings.tavily_api_key),
        ]:
            if usable_secret(key) and (kind != "github" or self.settings.github_repository):
                self.save(
                    owner,
                    kind,
                    ConnectionInput(
                        secret=key,
                        repository=self.settings.github_repository if kind == "github" else "",
                    ),
                )
                imported.append(kind)
        return {"imported": imported, "connections": self.list(owner)}
