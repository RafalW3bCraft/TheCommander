"""Release archives preserve public inputs and reproduce byte-for-byte."""

import hashlib
import json
import tarfile

from scripts import package_release


def test_identical_sources_produce_identical_archives(monkeypatch, tmp_path):
    (tmp_path / "docs/evidence").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "README.md").write_text("Public release\n")
    (tmp_path / "scripts/start.sh").write_text("#!/bin/sh\nexit 0\n")
    (tmp_path / ".env").write_text("PRIVATE_KEY=fixture-private-value\n")
    (tmp_path / "scripts/private-link.py").symlink_to(tmp_path / ".env")
    monkeypatch.setattr(package_release, "ROOT", tmp_path)
    monkeypatch.setattr(
        package_release.subprocess,
        "check_output",
        lambda command, **kwargs: (
            b"README.md\0scripts/start.sh\0.env\0scripts/private-link.py\0"
            if command[1] == "ls-files"
            else b"fixture-head\n"
        ),
    )
    archives = []
    manifests = []
    for timestamp in (1700000000, 1700003600):
        with monkeypatch.context() as clock:
            clock.setattr("time.time", lambda: timestamp)
            package_release.main()
        manifest = json.loads((tmp_path / "docs/evidence/release-manifest.json").read_text())
        archives.append((tmp_path / manifest["artifact"]).read_bytes())
        manifests.append(manifest)
    assert manifests[0]["source_sha256"] == manifests[1]["source_sha256"]
    assert archives[0] == archives[1], "Identical sources must retain the same archive digest"
    assert manifests[0]["artifact_sha256"] == hashlib.sha256(archives[1]).hexdigest()
    with tarfile.open(tmp_path / manifests[1]["artifact"]) as archive:
        assert archive.getnames() == ["TheCommander/README.md", "TheCommander/scripts/start.sh"]
        assert archive.extractfile("TheCommander/README.md").read() == b"Public release\n"
        assert archive.getmember("TheCommander/scripts/start.sh").mode == 0o755


def test_package_verification_rejects_stale_source_and_tampering(tmp_path):
    import io

    import pytest

    from scripts.verify_package import inspect_package

    (tmp_path / ".runtime/releases").mkdir(parents=True)
    source = tmp_path / "README.md"
    source.write_bytes(b"public")
    target = tmp_path / ".runtime/releases/release.tar.gz"
    with tarfile.open(target, "w:gz") as archive:
        info = tarfile.TarInfo("TheCommander/README.md")
        info.size = 6
        archive.addfile(info, io.BytesIO(b"public"))
    files = {"README.md": hashlib.sha256(b"public").hexdigest()}
    manifest = {
        "files": files,
        "artifact": str(target.relative_to(tmp_path)),
        "artifact_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "source_sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
    }
    assert inspect_package(tmp_path, manifest) == target.read_bytes()
    source.write_bytes(b"changed")
    with pytest.raises(ValueError, match="current checkout"):
        inspect_package(tmp_path, manifest)
    source.write_bytes(b"public")
    target.write_bytes(target.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="Archive digest"):
        inspect_package(tmp_path, manifest)


def test_package_verification_rejects_unsafe_entries(tmp_path):
    import io

    import pytest

    from scripts.verify_package import inspect_package

    (tmp_path / ".runtime/releases").mkdir(parents=True)
    (tmp_path / "README.md").write_bytes(b"public")
    target = tmp_path / ".runtime/releases/release.tar.gz"
    files = {"README.md": hashlib.sha256(b"public").hexdigest()}
    for kind in ("traversal", "symlink", "duplicate", "missing", "unexpected"):
        with tarfile.open(target, "w:gz") as archive:
            if kind != "missing":
                info = tarfile.TarInfo("TheCommander/README.md")
                info.size = 6
                if kind == "traversal":
                    info.name = "TheCommander/../README.md"
                if kind == "symlink":
                    info.type = tarfile.SYMTYPE
                    info.linkname = "../../README.md"
                if kind == "unexpected":
                    info.name = "TheCommander/extra.md"
                archive.addfile(info, io.BytesIO(b"public"))
                if kind == "duplicate":
                    archive.addfile(info, io.BytesIO(b"public"))
        manifest = {
            "files": files,
            "artifact": str(target.relative_to(tmp_path)),
            "artifact_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "source_sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
        }
        with pytest.raises(ValueError):
            inspect_package(tmp_path, manifest)
