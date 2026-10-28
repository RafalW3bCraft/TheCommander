"""Operational probes must reject unsafe targets before any writes or requests."""

import json
import runpy
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/compose_smoke.py"


@pytest.mark.parametrize(
    "configuration",
    [
        {},
        {"COMPOSE_SMOKE_URL": "http://localhost:8000"},
        {
            "COMPOSE_SMOKE_URL": "http://localhost:8002",
            "COMPOSE_PROJECT_NAME": "thecommander-cleancheck-0123456789",
        },
    ],
)
def test_unsafe_smoke_invocation_has_no_effects(monkeypatch, tmp_path, configuration):
    monkeypatch.chdir(tmp_path)
    for name in ("COMPOSE_SMOKE_URL", "COMPOSE_PROJECT_NAME", "COMPOSE_SMOKE_ROOT"):
        monkeypatch.delenv(name, raising=False)
    for name, value in configuration.items():
        monkeypatch.setenv(name, value)
    effects = []

    def forbidden(*args, **kwargs):
        effects.append("write or network client")
        raise AssertionError("Unsafe invocation reached a side effect")

    monkeypatch.setattr(Path, "mkdir", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr("httpx.Client", forbidden)
    with pytest.raises(SystemExit, match="isolated clean-release runner"):
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert effects == []


def test_runner_marker_binds_directory_project_and_target(monkeypatch, tmp_path):
    from scripts.compose_smoke import isolated_target

    root = tmp_path / "thecommander-cleancheck-fixture"
    (root / ".runtime").mkdir(parents=True)
    monkeypatch.chdir(root)
    project = "thecommander-cleancheck-0123456789"
    url = "http://localhost:8002"
    for key, value in {
        "COMPOSE_SMOKE_ROOT": str(root),
        "COMPOSE_PROJECT_NAME": project,
        "COMPOSE_SMOKE_URL": url,
    }.items():
        monkeypatch.setenv(key, value)
    marker = root / ".runtime/compose-smoke-isolation.json"
    marker.write_text(json.dumps({"root": str(root), "project": project, "url": url}))
    assert isolated_target() == (url, project)
    marker.write_text(json.dumps({"root": str(root), "project": "owner-project", "url": url}))
    with pytest.raises(SystemExit):
        isolated_target()
    marker.unlink()
    marker.symlink_to(root / "missing-marker")
    with pytest.raises(SystemExit):
        isolated_target()
