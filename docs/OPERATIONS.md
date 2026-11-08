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
Root `main.py` now launches only the supported API; it does not start the worker
or database. The original Flask entrypoint is retained in Git history; ADR004 records its retirement.

Configure connections in the UI. “Import configured server credentials” imports
real configured keys, not placeholders. GitHub needs a selected `owner/repository`;
Tavily needs approved research domains; enable workspace notes. Test connections
individually. Nebius validation is a real bounded model request and consumes usage.

## Verification

With Node 22.12+ (within Node 22) on PATH,
`TEST_DATABASE_URL=postgresql://... ./scripts/verify.sh` runs actual offline gates.
The database principal must create isolated schemas. With PostgreSQL 17 binaries,
`./scripts/test_db.sh` starts a loopback-only disposable cluster on 55432 and prints
the test URL. Install browser binaries once using
`cd frontend && npx playwright install chromium` (CI also installs OS dependencies).
No provider keys are required for offline tests. Explicit live check:
`uv run python -m scripts.live_smoke`. It sends only harmless fictional context,
records sanitized metadata, and performs no GitHub write. It exits 0 only when
model discovery, the tool proposal and its continuation all pass; exit 2 means
missing/placeholder credentials, and exit 1 means a failed provider/acceptance
check. Read the JSON evidence for the specific failure.

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

## Additional release drills

`uv run python -m scripts.clean_release_smoke` copies tracked/unignored source
without host dependencies or secrets into a temporary directory, starts the actual
startup script with new credentials and volumes on port 8002, checks API, worker,
notes and memory, then removes only that uniquely named test project and volumes.
It requires Docker/Compose access and a free port 8002.

`TEST_DATABASE_URL=postgresql://... uv run python -m scripts.backup_smoke` requires
a test database role allowed to create databases. It creates two isolated databases,
checks custom-format dump/restore and encrypted credential recovery, checks a notes
archive restore, and removes the test databases. It never selects application data.

`TEST_DATABASE_URL=postgresql://... uv run python -m scripts.evaluate_live` performs
30 fictional local tasks, with real Nebius inference on the 26 applicable cases.
`TEST_DATABASE_URL=postgresql://... uv run python -m scripts.live_research_smoke`
performs live Tavily validation and one authorized documentation search. Both use
temporary schemas and incur provider usage; neither authorizes GitHub writes.

Optional credential expiry is owner-supplied. The app enforces the stored instant;
it does not discover every provider's token expiry. A provider 401 remains an
invalid-credential response unless a known local expiry is present.

Migration 002 invalidates old pending/approved issue proposals whose exact preview
did not bind the correlation marker. Create a fresh proposal after upgrade; old
executed receipts remain visible. No existing public-schema data is transformed.

Migration 003 adds a nullable message-to-run association and an index. New context
assembly excludes future queued prompts and orders earlier replies before the
current prompt; historical messages retain their timestamp fallback. This is an
additive forward migration, with no automatic data-deleting downgrade. Apply
during a maintenance window: the transactional index creation is appropriate for
this owner-scale database, but has not been benchmarked on a large messages table.

ECC inventory and audit reproduction: `uv run python -m scripts.audit_repository`.
See `ECC_SETUP.md` for catalog provenance, actual application and evidence
limits. This command does not install or invoke the catalog's external tools.

## HTTPS overlay and final release upgrade (2026-10-25)

Use `compose.yaml` plus `compose.https.yaml` on the authorized Linux host. Set
`APP_DOMAIN` to the actual hostname in the operator environment. Point DNS to the
host and allow incoming TCP 80/443. Caddy provisions certificates automatically;
its data/config volumes must persist. The API remains loopback-bound for local
health checks. The application requires Secure cookies and the exact HTTPS origin.

```sh
docker compose --env-file .env.runtime -f compose.yaml -f compose.https.yaml config --quiet
docker compose --env-file .env.runtime -f compose.yaml -f compose.https.yaml up --build -d
```

Do not run deployment commands against a remote host until that deployment is
explicitly authorized. Preserve existing project names, volumes and encryption
keys. Before upgrading, back up database, notes, private environment and image
identity. Migration 004 is additive; restore to a separate database/notes volume
for a rollback drill and validate before switching traffic. Never delete volumes
to resolve a migration failure. Do not roll back to an executable that can bypass
new configuration policy without evaluating the policy/data compatibility.

After startup check HTTPS login, Secure cookies, configured origin, database
readiness, worker freshness, settings persistence, and the three workflows.
Monitor readiness and worker heartbeat throughout judge availability; verify
backups periodically. Maintain sufficient provider quota for judge evaluation.
Do not put live credentials in the public README, video or evidence files.

[Caddy reference](https://caddyserver.com/docs/quick-starts/reverse-proxy).
The proxy image digest is pinned; remote DNS/TLS and uptime remain unverified
until a real host is selected and tested. See SETTINGS.md for supported controls.

## Reproduce and verify a release package

Run `uv run python -m scripts.package_release`, then
`uv run python -m scripts.verify_package`. Packaging fixes both tar metadata and
gzip header time/name, so identical source inputs produce identical archive bytes
with the same pinned Python/compression runtime. The manifest records source and
archive SHA-256 values. Old source packages remain under `.runtime/releases`.

The verifier checks archive integrity, file membership, safe paths, absence of
links/duplicates, current checkout content and configured-secret exclusion before
executing anything. It then runs clean_release_smoke against the extracted source:
fresh local Compose build/start, API/worker recreation and persistence checks.
Only its disposable test project/volumes are removed. Port 8002 must be free;
inspect existing Compose projects before running. Repackage after source changes.

This command verifies our generated package only. Do not use it to execute an
unreviewed user-supplied archive. Archive comparison remains an isolated read-only
exercise after its local path is provided.

The 30-task evaluator now exits 1 when any required scenario fails and writes
`Blocked` to its evidence status. Success requires every expected scenario and
writes `Live verified`. Inspect per-case results and usage; a failed provider
response is not a simulated success. Preserve a failed report before explicitly
repeating a read-only probe. Never apply this retry approach to uncertain writes.

## Isolated probes and cleanup preservation

Do not invoke compose_smoke directly against an owner deployment. Only
clean_release_smoke supplies its explicit loopback URL, unique project, scratch
root and matching isolation marker. The helper refuses missing/mismatched values
before any writes or HTTP requests. This prevents accidental targeting; it is not
an authentication boundary against someone who deliberately forges local markers.

The October 28 cleanup preserved pre-change public files in
`.runtime/cleanup-20261028/baseline.tar.gz`. The public cleanup-removals.json records
its digest and removed-file hashes. Keep this archive until the final source and
historical provenance are safely published. Private environments, data, backups
and ECC installation were not removed. To recover an individual archived file,
inspect its path and hash first, and extract it into a separate temporary directory;
do not overwrite the current checkout or execute archived code automatically.

## Enhancement branch rollout boundary

The production upgrade is still under development. Migrations 006 and 007 are
additive and run transactionally on startup; preserve a backup before upgrading.
An older image is not a validated rollback against the upgraded schema: restore
the matching backup into a separate deployment. New owner defaults and legacy
run provider routing are tested independently of clean installation.

Run progress uses `/api/runs/{id}/events` with resumable SSE and authenticated GET
fallback. Disable reverse-proxy response buffering for this route and allow the
25-second bounded stream. Do not expose database ports or raw execution services.

OpenAI/Anthropic connections are optional and require their own API credentials.
Do not enter secrets into frontend build variables. The canonical public template
remains `env.release.example`; the ignored user-owned `.env.example` is preserved.
Mem0, coding/browser execution and new production controls remain unavailable
until their separate implementation and acceptance gates are completed.

## Optional memory service — enhancement acceptance

Follow [ADR005](adr/005-memory-index.md) for the explicit overlay and separate
secret names. Do not enable it on the preserved baseline. The main startup path
continues to work with the index disabled. The worker drains the durable index
outbox while idle; `/api/memory/index-status` reports owner-scoped pending/retry
counts and last synchronization. An unavailable index falls back visibly to
canonical lexical recall; inspect service health without printing tokens.

`verify.sh` now checks the separate frozen memory dependency installation and
its audit as well as application checks. The CPU-tagged torch distribution can
be absent from PyPI advisories; inspect the audit's skip diagnostics rather than
claiming every dependency was checked. Real local vector/model acceptance uses
`memory_service/.venv/bin/python -m memory_service.smoke --download-model` on
disposable resources, separately from controlled tests. The download flag permits
only the pinned public model; the runtime itself stays offline.

The existing backup smoke covers canonical PostgreSQL, including migration008;
it does not establish an optional-index restore. Before production activation,
back up or deterministically rebuild the index from canonical records, preserve
pending tombstones, test correction/deletion after restoration and document
retention. The seven-day soak and recovery objectives remain release gates.
