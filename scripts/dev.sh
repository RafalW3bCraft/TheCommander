#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --frozen
uv run python scripts/setup_runtime.py
npm --prefix frontend ci
npm --prefix frontend run build
uv run python -m commander.worker &
worker_pid=$!
trap 'kill "$worker_pid" 2>/dev/null || true' EXIT INT TERM
uv run uvicorn commander.api:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
