"""Package public release inputs only; never includes private environments or runtime data."""

import gzip
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP = {
    "Dockerfile",
    ".dockerignore",
    "compose.yaml",
    "compose.https.yaml",
    "pyproject.toml",
    "uv.lock",
    "env.release.example",
    "README.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES",
    "main.py",
    "docs/openapi.json",
    "docs/evidence/.gitkeep",
    ".gitignore",
}
PREFIXES = (
    "commander/",
    "frontend/src/",
    "frontend/e2e/",
    "scripts/",
    "tests/",
    "deploy/",
    ".github/",
)
FRONTEND = {
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/tsconfig.json",
    "frontend/vite.config.ts",
    "frontend/playwright.config.ts",
    "frontend/eslint.config.js",
    "frontend/index.html",
}
REQUIRED = (TOP | FRONTEND) - {"docs/evidence/.gitkeep"} | {
    "commander/api.py",
    "commander/worker.py",
    "frontend/src/main.tsx",
    "frontend/src/SettingsPage.tsx",
    "frontend/src/api.ts",
    "frontend/src/api-schema.d.ts",
    "frontend/src/style.css",
    "scripts/start.sh",
    "scripts/setup_runtime.py",
    "scripts/verify.sh",
    "scripts/verify_package.py",
    "deploy/Caddyfile",
    "commander/migrations/001_core.sql",
    "commander/migrations/002_exact_preview.sql",
    "commander/migrations/003_message_runs.sql",
    "commander/migrations/004_owner_settings.sql",
    "commander/migrations/005_usage_reservation.sql",
}


def main():
    candidates = (
        subprocess.check_output(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=ROOT)
        .decode()
        .split("\0")
    )
    paths = sorted(
        {
            p
            for p in candidates
            if p in TOP | FRONTEND
            or p.startswith(PREFIXES)
            or (p.startswith("docs/") and p.endswith(".md"))
        }
    )
    content = {}
    for relative in paths:
        path = ROOT / relative
        if path.is_file() and not path.is_symlink():
            content[relative] = path.read_bytes()
    missing = REQUIRED - content.keys()
    if missing:
        raise ValueError("Required release inputs missing or unsafe: " + ", ".join(sorted(missing)))
    hashes = {p: hashlib.sha256(data).hexdigest() for p, data in content.items()}
    identifier = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    release = ROOT / ".runtime/releases"
    release.mkdir(parents=True, exist_ok=True)
    target = release / ("thecommander-" + identifier[:12] + ".tar.gz")
    # Both tar and gzip metadata must be stable for repeatable artifact digests.
    with (
        target.open("wb") as output,
        gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w") as archive,
    ):
        for relative, data in content.items():
            info = tarfile.TarInfo("TheCommander/" + relative)
            info.size = len(data)
            info.mode = 0o755 if relative.endswith(".sh") else 0o644
            info.mtime = 0
            archive.addfile(info, io.BytesIO(data))
    manifest = {
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "source": "working-tree release inputs, including uncommitted implementation",
        "source_sha256": identifier,
        "artifact": str(target.relative_to(ROOT)),
        "artifact_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "files": hashes,
        "excluded": [
            "private environment",
            "runtime data",
            "development ECC catalogs",
            "Git history",
            "legacy runtime",
            "generated evidence",
        ],
    }
    (ROOT / "docs/evidence/release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: v for k, v in manifest.items() if k != "files"}, indent=2))


if __name__ == "__main__":
    main()
