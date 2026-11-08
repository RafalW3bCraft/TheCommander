from commander.errors import DomainError


def list_memory(db, owner, query="", project_id=None):
    if project_id is not None:
        from commander.projects import require

        require(db, owner, project_id)
        return db.all(
            "SELECT * FROM memories WHERE owner_id=%s AND (project_id=%s OR project_id IS NULL) AND (key ILIKE %s OR content ILIKE %s) ORDER BY updated_at DESC LIMIT 500",
            (owner, project_id, "%" + query + "%", "%" + query + "%"),
        )
    return db.all(
        "SELECT * FROM memories WHERE owner_id=%s AND (key ILIKE %s OR content ILIKE %s) ORDER BY updated_at DESC LIMIT 500",
        (owner, "%" + query + "%", "%" + query + "%"),
    )


def save_memory(db, owner, data, item_id=None):
    with db.connect() as conn:
        scope = data.project_id
        if item_id:
            current = conn.execute(
                "SELECT * FROM memories WHERE id=%s AND owner_id=%s FOR UPDATE", (item_id, owner)
            ).fetchone()
            if not current:
                raise DomainError("Memory changed or no longer exists; reload before editing", 409)
            if "project_id" not in data.model_fields_set:
                scope = current["project_id"]
            if scope != current["project_id"]:
                raise DomainError("Memory scope cannot change; create a new reviewed record", 409)
        if scope is not None:
            from commander.projects import owned

            owned(conn, owner, scope)
        if (
            data.kind == "inferred"
            and conn.execute(
                "SELECT 1 FROM memories WHERE owner_id=%s AND key=%s AND kind='explicit' AND (project_id IS NULL OR project_id=%s) AND (expires_at IS NULL OR expires_at>now())",
                (owner, data.key, scope),
            ).fetchone()
        ):
            raise DomainError("An explicit preference already exists for this key", 409)
        if item_id:
            row = conn.execute(
                """UPDATE memories SET project_id=%s,kind=%s,key=%s,content=%s,expires_at=%s,source='owner correction',updated_at=now(),revision=revision+1
                WHERE id=%s AND owner_id=%s AND revision=%s RETURNING *""",
                (
                    scope,
                    data.kind,
                    data.key,
                    data.content,
                    data.expires_at,
                    item_id,
                    owner,
                    data.revision,
                ),
            ).fetchone()
            if not row:
                raise DomainError("Memory changed or no longer exists; reload before editing", 409)
        else:
            row = conn.execute(
                "INSERT INTO memories(owner_id,kind,key,content,source,expires_at,project_id) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *",
                (
                    owner,
                    data.kind,
                    data.key,
                    data.content,
                    "owner entry",
                    data.expires_at,
                    scope,
                ),
            ).fetchone()
    return row


def recall(db, owner, project_id=None):
    # Admission/expiry first; explicit facts win over inferred facts, then the
    # selected project's fact wins over an owner-wide fact of the same kind/key.
    return db.all(
        """SELECT kind,key,content,source FROM (
          SELECT DISTINCT ON (key) kind,key,content,source,updated_at
          FROM memories WHERE owner_id=%s AND (project_id IS NULL OR project_id=%s)
          AND (expires_at IS NULL OR expires_at>now()) AND kind IN ('explicit','inferred')
          ORDER BY key,(kind='explicit') DESC,(project_id IS NOT NULL) DESC,updated_at DESC,id
        ) eligible ORDER BY (kind='explicit') DESC,updated_at DESC,key LIMIT 30""",
        (owner, project_id),
    )


def retrieve(db, owner, project_id, query, *, index=None, limit=5):
    """Hybrid ranking over canonical eligible records; index IDs are untrusted hints."""
    import re

    if project_id is not None:
        from commander.projects import require

        require(db, owner, project_id)
    # Priority rules apply before ranking: inferred cannot displace explicit,
    # and project facts of the same kind override owner-global records.
    hints = {}
    query_truncated = len(query) > 2000
    status = "disabled" if index is None else "ready"
    if index is not None:
        from commander.memory_index import IndexUnavailable

        try:
            for scope in [None, project_id] if project_id is not None else [None]:
                hits, shortened = index.search_with_status(
                    owner, scope, query[:2000], limit=min(limit, 20)
                )
                query_truncated = query_truncated or shortened
                for hit in hits:
                    hints[(hit.id, hit.revision)] = hit.score
        except IndexUnavailable:
            hints = {}
            status = "degraded"
    # Re-read canonical state after network retrieval so corrections/deletions
    # made while the index was responding cannot enter this context.
    rows = db.all(
        """SELECT * FROM (
          SELECT DISTINCT ON (key) * FROM memories
          WHERE owner_id=%s AND (project_id IS NULL OR project_id=%s)
          AND (expires_at IS NULL OR expires_at>now())
          ORDER BY key,(kind='explicit') DESC,(project_id IS NOT NULL) DESC,updated_at DESC,id
        ) eligible ORDER BY updated_at DESC,id LIMIT 500""",
        (owner, project_id),
    )
    terms = set(re.findall(r"\w+", query.lower()))
    ranked = []
    for row in rows:
        words = set(re.findall(r"\w+", (row["key"] + " " + row["content"]).lower()))
        lexical = len(terms & words) / max(1, len(terms))
        semantic = hints.get((str(row["id"]), row["revision"]), 0)
        if lexical or semantic:
            ranked.append((lexical + semantic, row))
    ranked.sort(key=lambda item: (-item[0], str(item[1]["id"])))
    return {
        "records": [row for _, row in ranked[:limit]],
        "method": "hybrid" if status == "ready" else "lexical",
        "index_status": status,
        "query_truncated": query_truncated,
    }
