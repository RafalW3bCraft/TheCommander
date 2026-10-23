#!/usr/bin/env bash
# Optional isolated PostgreSQL test cluster; never uses or resets application data.
set -euo pipefail
cd "$(dirname "$0")/.."
pg_bin=${PG_BIN:-/usr/lib/postgresql/17/bin}
mkdir -p .runtime
if [ ! -f .runtime/test-postgres/PG_VERSION ]; then
  "$pg_bin/initdb" -D .runtime/test-postgres --auth-local=trust --auth-host=trust > .runtime/test-postgres-init.log
fi
if ! "$pg_bin/pg_ctl" -D .runtime/test-postgres status >/dev/null 2>&1; then
  "$pg_bin/pg_ctl" -D .runtime/test-postgres -l .runtime/test-postgres.log -o '-h 127.0.0.1 -p 55432 -k /tmp' start
fi
printf 'Use TEST_DATABASE_URL=postgresql://%s@127.0.0.1:55432/postgres for isolated test schemas.\n' "$(id -un)"
