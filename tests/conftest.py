import uuid

import psycopg
import pytest
from cryptography.fernet import Fernet
from psycopg import sql

from commander.settings import Settings
from scripts.test_database import require_test_database_url


@pytest.fixture
def settings(tmp_path):
    cfg = Settings(
        _env_file=None,
        database_url=require_test_database_url(),
        database_schema="test_" + uuid.uuid4().hex,
        encryption_key=Fernet.generate_key().decode(),
        bootstrap_token="test-bootstrap-token-with-32-characters",
        workspace_root=tmp_path / "notes",
    )
    yield cfg
    with psycopg.connect(cfg.database_url) as conn:
        conn.execute(
            sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(cfg.database_schema))
        )
