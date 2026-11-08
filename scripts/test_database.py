"""Fail closed before test tools can create or remove PostgreSQL schemas.

Never log connection strings: they can include passwords and TLS key paths.
The operator must supply a disposable database with a separate restricted role.
"""

import os

from dotenv import dotenv_values
from psycopg.conninfo import conninfo_to_dict


def _identity(value):
    try:
        info = conninfo_to_dict(value)
        host = info.get("host", "localhost").lower()
        database = info.get("dbname", "")
        port = info.get("port", "5432")
        if not database or "," in host or "," in port:
            raise ValueError()
        if host in {"localhost", "127.0.0.1", "::1"} or host.startswith("/"):
            host = "loopback"
        return host, int(port), database
    except Exception:
        raise ValueError("Set an explicit disposable PostgreSQL TEST_DATABASE_URL") from None


def require_test_database_url(value=None, *, application_url=None):
    value = value if value is not None else os.environ.get("TEST_DATABASE_URL", "")
    if not value or not isinstance(value, str):
        raise ValueError("Set an explicit disposable PostgreSQL TEST_DATABASE_URL")
    target = _identity(value)
    if application_url is None:
        values = {**dotenv_values(".env"), **dotenv_values(".env.runtime"), **os.environ}
        application_url = values.get("DATABASE_URL")
    if application_url and target == _identity(application_url):
        raise ValueError("TEST_DATABASE_URL must not select the application database")
    return value
