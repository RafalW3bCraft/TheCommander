"""Create missing local-only secrets; never overwrite the user's .env."""

import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet

path = Path(".env.runtime")
if path.exists():
    print("Existing .env.runtime preserved.")
else:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write("ENCRYPTION_KEY=" + Fernet.generate_key().decode() + "\n")
        stream.write("BOOTSTRAP_TOKEN=" + secrets.token_urlsafe(36) + "\n")
        stream.write("APP_ORIGIN=http://localhost:8000\n")
    print("Created .env.runtime with mode 0600. Use its bootstrap token on first sign-in.")

existing = path.read_text()
if "POSTGRES_PASSWORD=" not in existing:
    with path.open("a") as stream:
        stream.write("POSTGRES_PASSWORD=" + secrets.token_hex(24) + "\n")
    print("Added a local Compose database password without changing existing settings.")
