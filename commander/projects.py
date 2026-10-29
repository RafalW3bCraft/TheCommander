"""Project boundaries remain owner scoped; optimistic edits never bypass conflicts."""

from commander.errors import DomainError


def owned(conn, owner, project_id=None):
    if project_id is None:
        row = conn.execute(
            "SELECT * FROM projects WHERE owner_id=%s AND is_default", (owner,)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM projects WHERE owner_id=%s AND id=%s", (owner, project_id)
        ).fetchone()
    if not row:
        raise DomainError("Project not found", 404)
    return row


def require(db, owner, project_id=None):
    with db.connect() as conn:
        return owned(conn, owner, project_id)


def create(db, owner, data):
    return db.one(
        "INSERT INTO projects(owner_id,name) VALUES (%s,%s) RETURNING *", (owner, data.name)
    )


def update(db, owner, project_id, data):
    with db.connect() as conn:
        owned(conn, owner, project_id)
        row = conn.execute(
            "UPDATE projects SET name=%s,revision=revision+1 WHERE id=%s AND owner_id=%s AND revision=%s RETURNING *",
            (data.name, project_id, owner, data.revision),
        ).fetchone()
        if not row:
            raise DomainError("Project changed; reload before editing", 409, "conflict")
        return row


def delete(db, owner, project_id, revision):
    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE id=%s AND owner_id=%s FOR UPDATE", (project_id, owner)
        ).fetchone()
        if not row:
            raise DomainError("Project not found", 404)
        if row["revision"] != revision:
            raise DomainError("Project changed; reload before deleting", 409, "conflict")
        if row["is_default"]:
            raise DomainError("The default project cannot be deleted", 409)
        # Do not destroy conversations, schedules or memory implicitly.
        for table in ("conversations", "runs", "schedules", "memories"):
            from psycopg import sql

            if conn.execute(
                sql.SQL("SELECT 1 FROM {} WHERE project_id=%s LIMIT 1").format(
                    sql.Identifier(table)
                ),
                (project_id,),
            ).fetchone():
                raise DomainError("Project contains retained records; deletion is blocked", 409)
        conn.execute("DELETE FROM projects WHERE id=%s AND owner_id=%s", (project_id, owner))
    return {"status": "deleted"}
