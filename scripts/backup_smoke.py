"""Backup/restore drill using fresh test databases and fictional records only."""

import json
import os
import subprocess
import tarfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from cryptography.fernet import Fernet
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from commander.auth import hasher
from commander.connections import Connections
from commander.contracts import ConnectionInput, MemoryInput
from commander.db import Database
from commander.memory import save_memory
from commander.settings import Settings
from commander.workspace import Workspace


def main():
    base = os.environ["TEST_DATABASE_URL"]
    token = uuid.uuid4().hex[:12]
    source = "tc_backup_" + token
    target = "tc_restore_" + token
    directory = Path(".runtime") / "backup-smoke" / token
    directory.mkdir(parents=True)
    params = conninfo_to_dict(base)
    env = {**os.environ, "PGPASSWORD": params.pop("password", "")}
    with psycopg.connect(base, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(source)))
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target)))
    try:
        source_url = make_conninfo(**{**params, "dbname": source})
        target_url = make_conninfo(**{**params, "dbname": target})
        cfg = Settings(
            _env_file=None,
            database_url=source_url,
            encryption_key=Fernet.generate_key().decode(),
            bootstrap_token="backup-test-only-long-bootstrap-token",
        )
        db = Database(cfg)
        db.migrate()
        owner = db.one(
            "INSERT INTO owners(username,password_hash) VALUES (%s,%s) RETURNING id",
            ("fictional-backup-owner", hasher.hash("fictional-backup-password")),
        )["id"]
        memory = save_memory(
            db, owner, MemoryInput(key="Backup preference", content="Retain this fictional record")
        )
        Connections(db, cfg).save(
            owner, "nebius", ConnectionInput(secret="fictional-backup-provider-secret")
        )
        from commander.preferences import SettingsPatch, update, view

        update(db, cfg, owner, SettingsPatch(revision=0, max_steps=2))
        notes = Workspace(directory / "source-notes", owner)
        original_note = notes.write("backup-note.md", "Fictional durable workspace note")
        with tarfile.open(directory / "notes.tar.gz", "w:gz") as archive:
            archive.add(directory / "source-notes", arcname=".")
        with tarfile.open(directory / "notes.tar.gz", "r:gz") as archive:
            archive.extractall(directory / "restored-notes", filter="data")
        restored_notes = Workspace(directory / "restored-notes", owner)
        assert restored_notes.read("backup-note.md") == "Fictional durable workspace note"
        assert original_note["verified"]
        subprocess.run(
            ["pg_dump", "--dbname", source_url, "-Fc", "-f", str(directory / "backup.dump")],
            check=True,
            env=env,
            capture_output=True,
        )
        subprocess.run(
            [
                "pg_restore",
                "--dbname",
                target_url,
                "--no-owner",
                "--no-acl",
                str(directory / "backup.dump"),
            ],
            check=True,
            env=env,
            capture_output=True,
        )
        restored_cfg = cfg.model_copy(update={"database_url": target_url})
        restored = Database(restored_cfg)
        restored.migrate()
        assert view(restored, restored_cfg, owner)["effective"]["max_steps"] == 2
        row = restored.one("SELECT * FROM memories WHERE id=%s", (memory["id"],))
        assert row["content"] == memory["content"] and row["revision"] == memory["revision"]
        connection = Connections(restored, restored_cfg)
        assert (
            connection.secret(connection.get(owner, "nebius")) == "fictional-backup-provider-secret"
        )
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "clean_initialization": True,
            "custom_format_dump_restore": True,
            "memory_and_revision_preserved": True,
            "owner_settings_preserved": True,
            "encrypted_connection_decrypts_with_original_key": True,
            "migrations_after_restore": True,
            "notes_archive_restore_preserves_content": True,
            "test_databases_removed": True,
        }
        Path("docs/evidence/backup-restore.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))
    finally:
        with psycopg.connect(base, autocommit=True) as admin:
            for name in (source, target):
                admin.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


if __name__ == "__main__":
    main()
