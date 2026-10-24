# ADR 002 — retire the legacy startup path without losing its source

Accepted 2026-10-24; supplements ADR 001.

Keeping an executable Flask `main.py` alongside the supported FastAPI application
allowed the familiar `python main.py` command to launch the obsolete command
surface. Those shell-oriented routes are outside the supported release authority
model. Leaving that startup ambiguity would undermine the isolation decision.

Preserve the original entrypoint byte-for-byte as `legacy/main.py.txt`, SHA256
`c02392b1ecdc6703056323dd7c801bff4c6937e92517ae8e0911481f3480c806`.
Replace only root `main.py` with a compatibility launcher for the supported API.
All other legacy modules, templates, static assets and schema remain preserved.
The archived file is intentionally non-executable and absent from the image.

The complete service startup remains `./scripts/start.sh`; direct `main.py`
launches only the API and does not imply a worker or database has been started.
Regression `test_release_has_no_legacy_command_routes` verifies that the release
does not expose the old command endpoints. Restoring the archive to execution
would require a separate security and migration decision.
