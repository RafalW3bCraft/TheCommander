"""Bounded, non-extracting validation of untrusted sandbox output archives."""

import base64
import hashlib
import re
import tarfile
from pathlib import PurePosixPath

from commander.errors import DomainError

MEDIA_TYPES = {".txt": "text/plain", ".csv": "text/csv", ".json": "application/json"}
MAX_SIZE = 1024 * 1024


def validate_item(name, data):
    extension = PurePosixPath(name).suffix.lower()
    if (
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_. -]{0,99}", name)
        or extension not in MEDIA_TYPES
        or len(data) > MAX_SIZE
    ):
        raise DomainError("Sandbox artifact was rejected", 422, "artifact_rejected")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        raise DomainError("Sandbox artifact must be UTF-8 text", 422, "artifact_rejected") from None
    return {
        "name": name,
        "media_type": MEDIA_TYPES[extension],
        "data": base64.b64encode(data).decode(),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def read_archive(stream):
    files: list[dict[str, str]] = []
    names = set()
    try:
        with tarfile.open(fileobj=stream, mode="r|") as archive:
            for member in archive:
                path = PurePosixPath(member.name)
                if member.isdir() and str(path) in {"output", "."}:
                    continue
                parts = path.parts
                # docker cp output/. creates entries rooted at output/ or ./.
                if parts and parts[0] == "output":
                    parts = parts[1:]
                if (
                    not member.isfile()
                    or len(parts) != 1
                    or path.is_absolute()
                    or ".." in path.parts
                    or len(files) >= 5
                    or member.size > MAX_SIZE
                    or member.size < 0
                    or parts[0] in names
                ):
                    raise ValueError()
                source = archive.extractfile(member)
                if source is None:
                    raise ValueError()
                data = source.read(MAX_SIZE + 1)
                if len(data) != member.size:
                    raise ValueError()
                files.append(validate_item(parts[0], data))
                names.add(parts[0])
    except (tarfile.TarError, ValueError, OSError):
        raise DomainError(
            "Sandbox artifact archive was rejected", 422, "artifact_rejected"
        ) from None
    return files
