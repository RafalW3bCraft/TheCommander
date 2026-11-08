from pathlib import Path

from psycopg import sql
from test_workflows import Vendor

from commander.auth import hasher
from commander.db import Database
from commander.worker import Worker


def test_upgrade_preserves_legacy_rows_and_executes_null_snapshot(settings):
    db = Database(settings)
    # Simulate the previous release's schema ledger without modifying installed migrations.
    with db.connect() as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(settings.database_schema)))
        conn.execute(
            sql.SQL("SET search_path TO {}, public").format(
                sql.Identifier(settings.database_schema)
            )
        )
        conn.execute(
            "CREATE TABLE schema_versions(version text PRIMARY KEY,applied_at timestamptz NOT NULL DEFAULT now())"
        )
        for path in sorted(Path("commander/migrations").glob("00[1-3]_*.sql")):
            conn.execute(path.read_text())
            conn.execute("INSERT INTO schema_versions(version) VALUES (%s)", (path.name,))
        owner = conn.execute(
            "INSERT INTO owners(username,password_hash) VALUES (%s,%s) RETURNING id",
            ("upgrade-owner", hasher.hash("fictional-upgrade-password")),
        ).fetchone()["id"]
        run = conn.execute(
            "INSERT INTO runs(owner_id,skill,skill_version,prompt) VALUES (%s,'conversation','conversation-v1','Continue after upgrade') RETURNING id",
            (owner,),
        ).fetchone()["id"]
    # Seed through the historical SQL contract; current services require current migrations.
    memory = db.one(
        "INSERT INTO memories(owner_id,kind,key,content,source) VALUES (%s,'explicit','upgrade','Preserve this preference','owner entry') RETURNING *",
        (owner,),
    )
    db.migrate()
    db.migrate()
    upgraded = db.one("SELECT project_id,mode FROM runs WHERE id=%s", (run,))
    assert upgraded["mode"] == "automate"
    assert db.one(
        "SELECT is_default FROM projects WHERE id=%s AND owner_id=%s",
        (upgraded["project_id"], owner),
    )["is_default"]
    assert (
        db.one("SELECT content FROM memories WHERE id=%s", (memory["id"],))["content"]
        == memory["content"]
    )
    assert (
        db.one("SELECT settings_snapshot FROM runs WHERE id=%s", (run,))["settings_snapshot"]
        is None
    )
    from commander.connections import Connections
    from commander.contracts import ConnectionInput

    Connections(db, settings).save(
        owner, "nebius", ConnectionInput(secret="fictional-upgrade-secret")
    )
    Worker(settings, Vendor().transport()).tick()
    assert db.one("SELECT status FROM runs WHERE id=%s", (run,))["status"] == "succeeded"
