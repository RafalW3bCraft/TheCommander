"""Opt-in REAL containers. No provider mocks establish live inference here."""

import json
import os

import pytest
from test_sandbox_policy import config

from commander.sandbox.runner import DockerRunner

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_SANDBOX_DOCKER") != "1",
    reason="Requires an explicitly configured real Docker runner",
)


def runtime():
    return config(
        sandbox_runtime=os.getenv("SANDBOX_TEST_RUNTIME", "runsc"),
        sandbox_timeout_seconds=10,
        sandbox_browser_domains=["example.com"],
    )


def test_real_offline_code_limits_and_no_secret_inheritance(monkeypatch):
    monkeypatch.setenv("VULTR_API_KEY", "sandbox-inheritance-canary-not-a-real-key")
    result = DockerRunner(runtime()).execute(
        "code",
        """
import os, socket
assert 'VULTR_API_KEY' not in os.environ
assert os.getuid() == 10001
try:
    open('/host-write-test', 'w')
    raise AssertionError('root filesystem unexpectedly writable')
except OSError:
    pass
try:
    socket.create_connection(('1.1.1.1', 443), timeout=1)
    raise AssertionError('network unexpectedly available')
except OSError:
    pass
print(6 * 7)
""",
    )
    assert result["stdout"].strip() == "42", result
    assert result["receipt"]["exit_code"] == 0
    assert result["receipt"]["destroyed"]
    assert result["receipt"]["network"] == "none"


def test_real_code_timeout_and_output_flood():
    cfg = runtime()
    cfg.sandbox_timeout_seconds = 5
    result = DockerRunner(cfg).execute("code", "while True: pass")
    assert result["receipt"]["destroyed"]
    assert result["receipt"]["stop_reason"] == "timeout" or result["receipt"]["exit_code"] != 0
    result = DockerRunner(cfg).execute("code", "while True: print('x' * 8192, flush=True)")
    assert result["receipt"]["stop_reason"] == "output_limit"
    assert result["receipt"]["destroyed"]


@pytest.mark.skipif(
    os.getenv("RUN_SANDBOX_BROWSER") != "1",
    reason="Requires built browser/gateway images and public HTTPS access",
)
def test_real_browser_observation_with_network_gateway():
    cfg = runtime()
    cfg.sandbox_timeout_seconds = 60
    result = DockerRunner(cfg).execute(
        "browser",
        json.dumps(
            {
                "url": "https://example.com/",
                "domains": ["example.com"],
                "approved": False,
                "steps": [],
            }
        ),
    )
    assert result["receipt"]["exit_code"] == 0, result
    evidence = json.loads(result["stdout"])
    assert evidence["title"] == "Example Domain"
    assert evidence["screenshot"] and evidence["actions_executed"] == 0
    assert result["receipt"]["destroyed"]
