# Operations

## Startup

Install Docker with Compose v2, uv 0.13.1 and Git. For fresh setup, copy
`env.release.example` to `.env` and enter only real provider keys. Preserve an
existing `.env`. Run `./scripts/start.sh`. This generates missing secrets in
`.env.runtime`, builds the frontend/API image, and starts PostgreSQL, API and a
separate worker. Visit http://localhost:8000, read the bootstrap token locally
from `.env.runtime`, and choose an owner password of at least 12 characters.
Never paste runtime secrets in chat, commits or logs.

If this Linux host uses Podman as its Docker wrapper, start its user API socket
with `systemctl --user start podman.socket` first. There is no remote deployment.

For an existing PostgreSQL development database, use `./scripts/dev.sh` instead.
It reads DATABASE_URL from the preserved `.env`; that server must be running.
Do not run the legacy `main.py` as the release entry point.

Configure connections in the UI. “Import configured server credentials” imports
real configured keys, not placeholders. GitHub needs a selected `owner/repository`;
Tavily needs approved research domains; enable workspace notes. Test connections
individually. Nebius validation is a real bounded model request and consumes usage.

## Verification

`TEST_DATABASE_URL=postgresql://... ./scripts/verify.sh` runs actual offline gates.
The database principal must create isolated schemas. With PostgreSQL 17 binaries,
`./scripts/test_db.sh` starts a loopback-only disposable cluster on 55432 and prints
the test URL. Install browser binaries once using
`cd frontend && npx playwright install chromium` (CI also installs OS dependencies).
No provider keys are required for offline tests. Explicit live check:
`uv run python -m scripts.live_smoke`. It sends only harmless fictional context,
records sanitized metadata, and performs no GitHub write.

## Production settings

Terminate HTTPS at a trusted reverse proxy. Set PRODUCTION=true and APP_ORIGIN to
its exact HTTPS origin; secure cookies are then mandatory. Keep the API port bound
to loopback or a private reverse-proxy network. Do not expose PostgreSQL. Store
ENCRYPTION_KEY/BOOTSTRAP_TOKEN/database password separately from database backups.
Never rotate ENCRYPTION_KEY without decrypting/re-encrypting existing connections;
otherwise re-enter provider credentials after restoring the original key.

`/health/live` is process liveness; `/health/ready` checks database access after
startup migrations. `/api/worker` reports heartbeat age; >30 seconds is offline.
Inspect `docker compose --env-file .env.runtime logs --tail 100 api worker`.
Compose limits log size and restarts failed services. Graceful worker shutdown
allows an active bounded run to finish. Abrupt death triggers lease recovery.

## Backup and restore

Stop worker/API for a consistent database-and-notes snapshot:

```sh
docker compose --env-file .env.runtime stop api worker
mkdir -p .runtime/backups
docker compose --env-file .env.runtime exec -T db pg_dump -U commander -d commander -Fc > .runtime/backups/commander.dump
docker compose --env-file .env.runtime run --rm --no-deps --entrypoint tar api -C /data/notes -czf - . > .runtime/backups/notes.tar.gz
docker compose --env-file .env.runtime start api worker
```

Store the dump, notes archive and encryption-key backup securely. Restore into a
new isolated deployment/database first, using `pg_restore --no-owner --no-acl`,
then restore notes with matching uid 10001 and the original encryption key.
Validate memory export, connection decryption and receipt counts before switching
traffic. Never use a destructive restore on the only existing copy. Review old
queued schedules before restarting a restored worker: they can become due.

## Upgrade, rollback and legacy import

Back up first. Build the new image and let transactional migrations complete
before starting workers. Database migrations use version tracking and an advisory
lock. Rollback means the prior image plus a separately validated matching backup;
no unsafe automatic down-migration is provided. Keep old volumes until acceptance.

Legacy files are not automatically imported. Run
`uv run python -m commander.cli import-legacy --owner OWNER --file memory_store.json`
for a dry run. It reports malformed keys/conflicts without dumping contents.
Add `--apply` only after review; this backs up the original file and imports all
validated records transactionally. Existing public SQL tables remain untouched;
export and review them before explicit transformation. Fictional demo preference:
`uv run python -m commander.cli seed --owner OWNER`.
