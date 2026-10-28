"""Build/start a clean source snapshot, with fresh local secrets and no provider keys.

Uses an isolated Compose project on port 8002. Removes only its own disposable
volumes afterwards. Existing application projects and data are never selected.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


def main():
    source = Path.cwd()
    project = "thecommander-cleancheck-" + uuid.uuid4().hex[:10]
    env = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "HOME", "XDG_RUNTIME_DIR", "DOCKER_HOST", "CONTAINER_HOST"}
    }
    env.update(COMPOSE_PROJECT_NAME=project, APP_PORT="8002")
    paths = subprocess.check_output(["git", "ls-files", "-co", "--exclude-standard", "-z"]).split(
        b"\0"
    )
    with tempfile.TemporaryDirectory(prefix="thecommander-cleancheck-") as tmp:
        root = Path(tmp)
        env["COMPOSE_SMOKE_ROOT"] = str(root.resolve())
        for raw in set(paths):
            if not raw:
                continue
            relative = Path(os.fsdecode(raw))
            if relative.parts[0] == ".agents":
                continue  # Owner's development catalog is not a release dependency.
            original = source / relative
            if original.is_file() and not original.is_symlink():
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, target)
        assert not (root / ".env").exists() and not (root / ".env.runtime").exists()
        assert not (root / ".venv").exists() and not (root / "frontend/node_modules").exists()
        shutil.copy2(root / "env.release.example", root / ".env")
        subprocess.run([sys.executable, "scripts/setup_runtime.py"], cwd=root, env=env, check=True)
        runtime = root / ".env.runtime"
        runtime.write_text(runtime.read_text().replace("localhost:8000", "localhost:8002"))
        (root / ".runtime").mkdir(exist_ok=True)
        (root / ".runtime/compose-smoke-isolation.json").write_text(
            json.dumps(
                {"root": str(root.resolve()), "project": project, "url": "http://localhost:8002"}
            )
        )
        compose = ["docker", "compose", "--env-file", ".env.runtime"]
        try:
            subprocess.run(["bash", "scripts/start.sh"], cwd=root, env=env, check=True)
            subprocess.run(
                [sys.executable, "scripts/compose_smoke.py"],
                cwd=root,
                env={**env, "COMPOSE_SMOKE_URL": "http://localhost:8002"},
                check=True,
            )
            subprocess.run(
                compose + ["up", "--force-recreate", "--no-build", "-d", "api", "worker"],
                cwd=root,
                env=env,
                check=True,
            )
            subprocess.run(
                [sys.executable, "scripts/compose_smoke.py"],
                cwd=root,
                env={**env, "COMPOSE_SMOKE_URL": "http://localhost:8002"},
                check=True,
            )
            report = json.loads((root / "docs/evidence/compose-smoke.json").read_text())
            report.update(
                timestamp=datetime.now(timezone.utc).isoformat(),
                source="tracked and unignored working-tree snapshot excluding .agents development catalog; no host dependencies or secrets",
                startup="./scripts/start.sh",
                external_credentials=False,
            )
        finally:
            subprocess.run(compose + ["down", "--volumes"], cwd=root, env=env, check=True)
        report["disposable_project_removed"] = True
        (source / "docs/evidence/clean-release-smoke.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
