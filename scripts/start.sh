#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --frozen
uv run python scripts/setup_runtime.py
docker compose --env-file .env.runtime up --build -d
printf 'Open http://localhost:%s. Bootstrap token is in .env.runtime.\n' "${APP_PORT:-8000}"
