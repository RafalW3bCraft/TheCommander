# Preserved historical entrypoint

`main.py.txt` is the byte-for-byte original Flask launcher/routes, archived during
the recursive audit on 2026-10-23. It is reference material, not an executable
release entrypoint. It had unauthenticated shell/filesystem/HTTP routes, a default
session secret, debug mode and arbitrary image proxying. Those routes are not
served by the release and must not be re-enabled on an exposed server.

The remaining historical root modules (`agent.py`, `ai_service.py`,
`command_center.py`, `config.py`, `task_service.py`, `tools.py`, `utils.py`),
`agents/`, `templates/`, `static/`, `requirements.txt` and `schema.sql` are retained
for provenance and explicit data migration. They are absent from the release
image and import graph. No old database or JSON data was deleted or imported.
Root `main.py` now launches the FastAPI release, with no old route imports.

Do not install the old unpinned dependencies to run the new release. Use
`uv sync --frozen` or `./scripts/start.sh` and follow the root README.
Historical feature claims and setup are in docs/LEGACY_README.md and are not a
current capability list. See docs/CODEBASE_AUDIT.md for the module inventory,
retirement decisions and supported workflows.
