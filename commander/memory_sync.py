"""Durable, idempotent synchronization of canonical memory into a derived index."""

from commander.memory_index import IndexUnavailable, MemoryIndex


def configured_index(settings):
    if not settings.memory_index_url:
        return None
    return MemoryIndex(settings.memory_index_url, settings.memory_index_token)


def sync_one(db, index):
    # Expiry may occur without a canonical write. Queue removal for previously
    # indexed records. Canonical admission excludes them immediately regardless.
    with db.connect() as conn:
        conn.execute("""INSERT INTO memory_index_jobs(memory_id,owner_id,project_id,revision,deleted)
          SELECT memory_id,owner_id,project_id,revision,true FROM memory_index_state
          WHERE expires_at<=now() ON CONFLICT(memory_id) DO NOTHING""")
        job = conn.execute("""SELECT * FROM memory_index_jobs WHERE available_at<=now()
          AND (lease_until IS NULL OR lease_until<now())
          ORDER BY available_at,memory_id LIMIT 1 FOR UPDATE SKIP LOCKED""").fetchone()
        if not job:
            return False
        conn.execute(
            "UPDATE memory_index_jobs SET lease_until=now()+interval '45 seconds',attempts=attempts+1 WHERE memory_id=%s",
            (job["memory_id"],),
        )
    row = db.one(
        "SELECT *, (expires_at IS NULL OR expires_at>now()) AS eligible FROM memories WHERE id=%s AND owner_id=%s",
        (job["memory_id"], job["owner_id"]),
    )
    # A concurrent correction/deletion replaces this job. Never acknowledge it
    # using a stale revision; the next worker dispatch handles the new record.
    if row and row["revision"] != job["revision"]:
        return True
    deleting = job["deleted"] or not row or not row["eligible"]
    truncated = False
    try:
        if deleting:
            index.delete(job["owner_id"], job["project_id"], job["memory_id"], job["revision"])
        else:
            truncated = (
                bool(
                    index.upsert(
                        job["owner_id"],
                        job["project_id"],
                        job["memory_id"],
                        job["revision"],
                        (row["key"] + "\n" + row["content"])[:4000],
                    )
                )
                or len(row["key"] + "\n" + row["content"]) > 4000
            )
    except IndexUnavailable:
        db.one(
            """UPDATE memory_index_jobs SET lease_until=NULL,last_error='index_unavailable',
              available_at=now()+make_interval(secs => %s)
              WHERE memory_id=%s AND revision=%s AND deleted=%s RETURNING memory_id""",
            (
                min(300, 2 ** min(job["attempts"] + 1, 8)),
                job["memory_id"],
                job["revision"],
                job["deleted"],
            ),
        )
        return True
    with db.connect() as conn:
        acknowledged = conn.execute(
            "DELETE FROM memory_index_jobs WHERE memory_id=%s AND revision=%s AND deleted=%s RETURNING memory_id",
            (job["memory_id"], job["revision"], job["deleted"]),
        ).fetchone()
        if acknowledged:
            if deleting:
                conn.execute(
                    "DELETE FROM memory_index_state WHERE memory_id=%s", (job["memory_id"],)
                )
            else:
                conn.execute(
                    """INSERT INTO memory_index_state(memory_id,owner_id,project_id,revision,expires_at,truncated)
                  VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(memory_id) DO UPDATE SET
                  revision=EXCLUDED.revision,expires_at=EXCLUDED.expires_at,truncated=EXCLUDED.truncated,synced_at=now()""",
                    (
                        job["memory_id"],
                        job["owner_id"],
                        job["project_id"],
                        job["revision"],
                        row["expires_at"],
                        truncated,
                    ),
                )
    return True
