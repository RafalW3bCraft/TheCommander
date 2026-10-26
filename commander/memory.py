from commander.errors import DomainError


def list_memory(db, owner, query=""):
    return db.all(
        "SELECT * FROM memories WHERE owner_id=%s AND (key ILIKE %s OR content ILIKE %s) ORDER BY updated_at DESC LIMIT 500",
        (owner, "%" + query + "%", "%" + query + "%"),
    )


def save_memory(db, owner, data, item_id=None):
    with db.connect() as conn:
        if (
            data.kind == "inferred"
            and conn.execute(
                "SELECT 1 FROM memories WHERE owner_id=%s AND key=%s AND kind='explicit' AND (expires_at IS NULL OR expires_at>now())",
                (owner, data.key),
            ).fetchone()
        ):
            raise DomainError("An explicit preference already exists for this key", 409)
        if item_id:
            row = conn.execute(
                """UPDATE memories SET kind=%s,key=%s,content=%s,expires_at=%s,source='owner correction',updated_at=now(),revision=revision+1
                WHERE id=%s AND owner_id=%s AND revision=%s RETURNING *""",
                (data.kind, data.key, data.content, data.expires_at, item_id, owner, data.revision),
            ).fetchone()
            if not row:
                raise DomainError("Memory changed or no longer exists; reload before editing", 409)
        else:
            row = conn.execute(
                "INSERT INTO memories(owner_id,kind,key,content,source,expires_at) VALUES (%s,%s,%s,%s,%s,%s) RETURNING *",
                (owner, data.kind, data.key, data.content, "owner entry", data.expires_at),
            ).fetchone()
    return row


def recall(db, owner):
    # Explicit preferences win; expired entries never enter active context.
    return db.all(
        """SELECT kind,key,content,source FROM memories m WHERE owner_id=%s
      AND (expires_at IS NULL OR expires_at>now()) AND kind IN ('explicit','inferred')
      AND (kind='explicit' OR NOT EXISTS(SELECT 1 FROM memories e WHERE e.owner_id=m.owner_id AND e.key=m.key AND e.kind='explicit' AND (e.expires_at IS NULL OR e.expires_at>now())))
      ORDER BY (kind='explicit') DESC,updated_at DESC LIMIT 30""",
        (owner,),
    )
