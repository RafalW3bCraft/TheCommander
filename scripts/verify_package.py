"""Verify our generated release against this checkout, then test its clean startup.

This is not an importer for user-supplied archives. Every archive byte must match
its manifest and every included source file must match the current checkout before
any extracted script executes. Existing application projects/data are not selected.
"""

import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def inspect_package(root, manifest):
    root = root.resolve()
    target = root / manifest["artifact"]
    if target.is_symlink() or target.resolve().parent != root / ".runtime/releases":
        raise ValueError("Package must be a generated local release file")
    archive_bytes = target.read_bytes()
    if sha256(archive_bytes) != manifest["artifact_sha256"]:
        raise ValueError("Archive digest does not match the manifest")
    files = manifest["files"]
    if sha256(json.dumps(files, sort_keys=True).encode()) != manifest["source_sha256"]:
        raise ValueError("Source fingerprint does not match the manifest")
    for relative, digest in files.items():
        path = PurePosixPath(relative)
        source = root / relative
        if (
            path.is_absolute()
            or ".." in path.parts
            or any(
                p in {".env", ".env.runtime", ".git", ".runtime", ".venv", "node_modules"}
                for p in path.parts
            )
            or str(path) != relative
            or source.is_symlink()
            or not source.resolve().is_relative_to(root)
            or not source.is_file()
            or sha256(source.read_bytes()) != digest
        ):
            raise ValueError("Packaged source does not match the current checkout")
    secrets = []
    for name in (".env", ".env.runtime"):
        for key, value in dotenv_values(root / name).items():
            if (
                value
                and len(value) > 15
                and any(s in key for s in ("TOKEN", "KEY", "SECRET", "PASSWORD"))
                and not any(s in value.lower() for s in ("your-", "change-this", "placeholder"))
            ):
                secrets.append(value.encode())
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
        for item in archive:
            path = PurePosixPath(item.name)
            if (
                not item.isfile()
                or path.is_absolute()
                or ".." in path.parts
                or str(path) != item.name
                or path.parts[0] != "TheCommander"
            ):
                raise ValueError("Unsafe archive entry")
            relative = "/".join(path.parts[1:])
            if relative not in files or relative in seen:
                raise ValueError("Unexpected or duplicate archive entry")
            source = root / relative
            if item.size != source.stat().st_size:
                raise ValueError("Archive entry size does not match source")
            stream = archive.extractfile(item)
            if stream is None:
                raise ValueError("Archive entry is not readable")
            data = stream.read()
            if sha256(data) != files[relative]:
                raise ValueError("Archive content does not match source")
            if any(secret in data for secret in secrets):
                raise ValueError("Configured secret detected in archive")
            seen.add(relative)
    if seen != set(files):
        raise ValueError("Archive is missing source files")
    return archive_bytes


def main():
    manifest = json.loads((ROOT / "docs/evidence/release-manifest.json").read_text())
    artifact = inspect_package(ROOT, manifest)
    with tempfile.TemporaryDirectory(prefix="thecommander-packaged-") as tmp:
        with tarfile.open(fileobj=io.BytesIO(artifact), mode="r:gz") as archive:
            archive.extractall(tmp, filter="data")
        source = Path(tmp) / "TheCommander"
        subprocess.run(["git", "init", "-q"], cwd=source, check=True)
        subprocess.run(["git", "add", "."], cwd=source, check=True)
        subprocess.run(
            [sys.executable, "-m", "scripts.clean_release_smoke"], cwd=source, check=True
        )
        operational = json.loads((source / "docs/evidence/clean-release-smoke.json").read_text())
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "Locally verified",
        "head": manifest["head"],
        "source_sha256": manifest["source_sha256"],
        "artifact": manifest["artifact"],
        "artifact_sha256": manifest["artifact_sha256"],
        "verified_files": len(manifest["files"]),
        "archive_paths_links_hashes_and_configured_secret_scan": "passed",
        "clean_build_start_and_retained_volume_checks": operational,
        "external_credentials": False,
        "remote_deployment": "Not run",
    }
    (ROOT / "docs/evidence/packaged-release-verification.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
