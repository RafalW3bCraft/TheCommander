"""A failed or blocked live probe must not signal success to release automation."""

import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

from commander import providers, settings
from commander.errors import DomainError

PROBE = Path(__file__).resolve().parents[1] / "scripts/live_smoke.py"


@pytest.mark.parametrize(
    ("mode", "exit_code", "status"),
    [
        ("missing", 2, "Blocked"),
        ("unavailable_model", 1, "Blocked"),
        ("provider_error", 1, "Blocked"),
        ("invalid_tool", 1, "Blocked"),
        ("empty_final", 1, "Blocked"),
        ("success", 0, "Live verified"),
    ],
)
def test_live_probe_exit_matches_evidence(monkeypatch, tmp_path, mode, exit_code, status):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    monkeypatch.setattr(
        settings,
        "Settings",
        lambda: SimpleNamespace(
            nebius_api_key="" if mode == "missing" else "test-probe-credential",
            nebius_model="nvidia/test-model",
            nebius_base_url="https://api.tokenfactory.nebius.com/v1",
        ),
    )

    class ControlledProvider:
        def __init__(self, config):
            self.config = config

        def request(self, *args, **kwargs):
            if mode == "provider_error":
                raise DomainError("Provider unavailable", 502, "provider_error")
            return {"data": [] if mode == "unavailable_model" else [{"id": "nvidia/test-model"}]}

        def completion(self, secret, messages, tools=None, timeout=30):
            if tools:
                return (
                    {
                        "tool_calls": [
                            {
                                "id": "probe-call",
                                "type": "function",
                                "function": {
                                    "name": "echo_check",
                                    "arguments": json.dumps(
                                        {"word": "wrong" if mode == "invalid_tool" else "verified"}
                                    ),
                                },
                            }
                        ]
                    },
                    {"total_tokens": 10},
                    1,
                )
            return {"content": "" if mode == "empty_final" else "verified"}, {"total_tokens": 5}, 1

    monkeypatch.setattr(providers, "Provider", ControlledProvider)
    with pytest.raises(SystemExit) as result:
        runpy.run_path(str(PROBE), run_name="__main__")
    assert result.value.code == exit_code
    report = json.loads((tmp_path / "docs/evidence/live-smoke.json").read_text())
    assert report["status"] == status
    assert report["passed"] is (mode == "success")
    # This test uses an explicitly controlled transport, never live provider success.
