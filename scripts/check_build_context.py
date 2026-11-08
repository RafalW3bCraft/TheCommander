"""Exercise Docker ignore semantics with fictional canaries, never real secrets."""

import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from commander.settings import Settings


def main():
    image = Settings.model_fields["sandbox_code_image"].default
    tag = "localhost/commander-context-check:" + uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix="commander-context-check-") as directory:
        root = Path(directory)
        shutil.copyfile(".dockerignore", root / ".dockerignore")
        admitted = ["deploy/sandbox/browser.py", "deploy/sandbox/proxy.py"]
        excluded = [
            ".env",
            ".env.runtime",
            ".env.private",
            "deploy/sandbox/private.env",
            "deploy/private.env",
            "commander/.env.private",
            ".runtime/private",
            ".git/config",
            ".venv/private",
            ".tools/private",
            "frontend/node_modules/private",
        ]
        for name in admitted + excluded:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fictional build-context canary")
        check = (
            "from pathlib import Path; p=Path('/context'); "
            f"assert all((p/x).is_file() for x in {admitted!r}); "
            f"assert not any((p/x).exists() for x in {excluded!r}); "
            "print('Required sandbox sources admitted; all private canaries excluded')"
        )
        (root / "Dockerfile").write_text(
            f'FROM {image}\nCOPY . /context\nRUN python -c "{check}"\n'
        )
        try:
            subprocess.run(["docker", "build", "-t", tag, str(root)], check=True)
        finally:
            # Remove only this invocation's unique tag, never prune shared data.
            subprocess.run(["docker", "image", "rm", tag], check=False)


if __name__ == "__main__":
    main()
