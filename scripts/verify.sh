#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --frozen
uv run ruff check commander tests scripts
uv run ruff format --check commander tests scripts
uv run mypy commander
uv run pytest --cov=commander --cov-report=term-missing
uv run python -m scripts.export_openapi
npm --prefix frontend ci
npm --prefix frontend run api:types
npm --prefix frontend run format:check
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend run test:e2e
uv run pip-audit --local --skip-editable
npm --prefix frontend audit --audit-level=high
uv run python scripts/scan_secrets.py
