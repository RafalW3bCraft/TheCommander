"""Test setup must never infer the application database."""

import pytest

from scripts.test_database import require_test_database_url


@pytest.mark.parametrize("value", [None, "", "sqlite:///tmp/test.db", "not a connection"])
def test_missing_or_invalid_test_database_is_rejected(value, monkeypatch):
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="disposable PostgreSQL"):
        require_test_database_url(value, application_url="postgresql://owner@localhost:5433/app")


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "[::1]"])
def test_application_database_is_rejected_despite_other_user_or_loopback_alias(host):
    with pytest.raises(ValueError, match="application database"):
        require_test_database_url(
            f"postgresql://test_user@{host}:5433/app",
            application_url="postgresql://owner@127.0.0.1:5433/app",
        )


def test_explicit_separate_database_is_accepted():
    target = "postgresql://test_user@127.0.0.1:55432/commander_test"
    assert (
        require_test_database_url(target, application_url="postgresql://owner@127.0.0.1:5433/app")
        == target
    )


def test_error_never_contains_credentials():
    with pytest.raises(ValueError) as exc:
        require_test_database_url("postgresql://user:fictional-private-password@host/")
    assert "fictional-private-password" not in str(exc.value)
