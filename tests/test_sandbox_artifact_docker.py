"""Opt-in real code artifacts and denied filesystem/network access."""

import base64
import os

import pytest
from test_sandbox_docker import runtime

from commander.sandbox.runner import DockerRunner

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_SANDBOX_DOCKER") != "1", reason="Requires real Docker"
)


def test_real_bounded_csv_export_before_removal():
    result = DockerRunner(runtime()).execute(
        "code",
        "from pathlib import Path\nPath('/tmp/output/answer.csv').write_text('answer\\n42\\n')\nprint(42)",
    )
    assert result["stdout"].strip() == "42", result
    assert result["receipt"]["exit_code"] == 0 and result["receipt"]["destroyed"], result
    assert result["receipt"]["stop_reason"] is None, result
    assert result["artifacts"][0]["name"] == "answer.csv"
    assert base64.b64decode(result["artifacts"][0]["data"]) == b"answer\n42\n"


def test_real_symlink_export_is_denied_and_removed():
    result = DockerRunner(runtime()).execute(
        "code", "import os\nos.symlink('/etc/passwd','/tmp/output/secret.txt')"
    )
    assert result["receipt"]["stop_reason"] == "artifact_rejected", result
    assert result["receipt"]["destroyed"]
    assert not result["artifacts"]
