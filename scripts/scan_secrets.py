"""Check release source/bundles for private runtime values without printing them."""

import subprocess
from pathlib import Path

from dotenv import dotenv_values

values = []
for filename in (".env", ".env.runtime"):
    for key, value in dotenv_values(filename).items():
        if (
            value
            and len(value) > 15
            and any(part in key for part in ("TOKEN", "KEY", "SECRET", "PASSWORD"))
            and not any(part in value.lower() for part in ("your-", "change-this", "placeholder"))
        ):
            values.append(value.encode())
files = subprocess.check_output(["git", "ls-files", "-co", "--exclude-standard", "-z"]).split(b"\0")
paths = [Path(p.decode()) for p in files if p] + list(Path("frontend/dist").glob("**/*"))
failures = []
for path in paths:
    if path.is_file() and path.name not in (".env", ".env.runtime"):
        data = path.read_bytes()
        if any(value in data for value in values):
            failures.append(str(path))
if failures:
    raise SystemExit("Private value detected in: " + ", ".join(failures))
print(
    "No configured private runtime values found in tracked/unignored release files or frontend bundle."
)
