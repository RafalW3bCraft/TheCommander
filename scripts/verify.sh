#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --frozen
uv run ruff check main.py commander memory_service tests scripts
uv run ruff format --check main.py commander memory_service tests scripts
uv run mypy commander
uv run pytest --cov=commander --cov-report=term-missing
uv run python -m scripts.export_openapi
npm --prefix frontend ci
npm --prefix frontend run api:types
npm --prefix frontend run format:check
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend run test:e2e
uv run pip-audit --local --skip-editable --timeout 60
uv sync --project memory_service --frozen
memory_site_packages="$(memory_service/.venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
uv run pip-audit --path "$memory_site_packages" --skip-editable --timeout 60
npm --prefix frontend audit --audit-level=high
uv run python scripts/scan_secrets.py
