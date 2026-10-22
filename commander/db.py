from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def json(value):
    return Jsonb(value)


class Database:
    def __init__(self, settings):
        self.settings = settings

    @contextmanager
    def connect(self):
        with psycopg.connect(
            self.settings.database_url, row_factory=dict_row, connect_timeout=5
        ) as conn:
            conn.execute(
                sql.SQL("SET search_path TO {}, public").format(
                    sql.Identifier(self.settings.database_schema)
                )
            )
            conn.execute("SET statement_timeout = '15s'")
            yield conn

    def migrate(self):
        with self.connect() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(714893)")
            conn.execute(
                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                    sql.Identifier(self.settings.database_schema)
                )
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_versions (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            for path in sorted(Path(__file__).with_name("migrations").glob("*.sql")):
                if not conn.execute(
                    "SELECT 1 FROM schema_versions WHERE version=%s", (path.name,)
                ).fetchone():
                    conn.execute(path.read_text())
                    conn.execute("INSERT INTO schema_versions(version) VALUES (%s)", (path.name,))

    def one(self, query, params=()):
        with self.connect() as conn:
            return conn.execute(query, params).fetchone()

    def all(self, query, params=()):
        with self.connect() as conn:
            return conn.execute(query, params).fetchall()
