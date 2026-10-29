#!/bin/sh
set -eu
# Runs only on a newly initialized, dedicated volume; never against Commander DB.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --set=memory_password="$MEMORY_DB_PASSWORD" <<'SQL'
CREATE EXTENSION IF NOT EXISTS vector;
SELECT format('CREATE ROLE memory_index LOGIN PASSWORD %L', :'memory_password') \gexec
GRANT CONNECT ON DATABASE memory_index TO memory_index;
GRANT USAGE, CREATE ON SCHEMA public TO memory_index;
SQL
