"""Failed live acceptance must fail the release command, without real I/O here."""

from contextlib import nullcontext
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet

from commander.settings import Settings
from scripts import evaluate_live


@pytest.mark.parametrize("succeeds", [False, True])
def test_live_scenario_exit_matches_persisted_evidence(monkeypatch, tmp_path, succeeds):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs/evidence").mkdir(parents=True)
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://fixture/unused")
    config = Settings(
        _env_file=None,
        database_url="postgresql://fixture/unused",
        encryption_key=Fernet.generate_key().decode(),
        bootstrap_token="test-only-bootstrap-token-not-for-production",
        nebius_api_key="test-only-evaluation-credential",
    )
    monkeypatch.setattr(evaluate_live, "Settings", lambda: config)
    monkeypatch.setattr(evaluate_live, "create_app", lambda settings: None)

    class Response:
        def __init__(self, data):
            self.data = data

        def json(self):
            return self.data

        def raise_for_status(self):
            return self

    class FailedApplication:
        def __init__(self, app):
            self.headers = {}
            self.case = -1

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, path, **kwargs):
            if path == "/api/runs":
                self.case += 1
            return Response({"id": "fixture-id", "csrf": "fixture-csrf"})

        def put(self, *args, **kwargs):
            return Response({})

        def delete(self, *args, **kwargs):
            return Response({})

        def get(self, path):
            if succeeds:
                return Response(
                    {
                        "status": "cancelled"
                        if self.case in (26, 27)
                        else "failed"
                        if self.case in (28, 29)
                        else "succeeded",
                        "result": "GOLDFIN"
                        if self.case == 24
                        else "unknown"
                        if self.case == 25
                        else "BLUEFIN",
                        "events": [{"kind": "note_receipt"}] if self.case in (18, 19, 20) else [],
                        "actions": [],
                    }
                )
            return Response(
                {"status": "failed", "events": [], "actions": [], "error": "Fixture failure"}
            )

    monkeypatch.setattr(evaluate_live, "TestClient", FailedApplication)
    monkeypatch.setattr(
        evaluate_live.subprocess,
        "Popen",
        lambda *args, **kwargs: SimpleNamespace(terminate=lambda: None, wait=lambda **kw: None),
    )
    monkeypatch.setattr(
        evaluate_live.psycopg,
        "connect",
        lambda *args, **kwargs: nullcontext(SimpleNamespace(execute=lambda *a: None)),
    )
    if succeeds:
        evaluate_live.main()
    else:
        with pytest.raises(SystemExit) as outcome:
            evaluate_live.main()
        assert outcome.value.code == 1
    import json

    report = json.loads((tmp_path / "docs/evidence/live-evaluation.json").read_text())
    assert report["sample_size"] == 30
    assert (report["passed"] == report["sample_size"]) is succeeds
    assert report["status"] == ("Live verified" if succeeds else "Blocked")
