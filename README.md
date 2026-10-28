# TheCommander — Personal AI

An owner-controlled engineering assistant with persistent memory, three reusable
skills, scoped connections, scheduled background work and exact approval for
GitHub writes. Release 0.2.0 rebuilds the application around FastAPI, React,
PostgreSQL and a separate worker. The obsolete Flask runtime has been retired from the working tree; Git history
and a hashed local archive preserve its source. See [architecture](docs/ARCHITECTURE.md).

**FINAL CLEANUP VERIFICATION IN PROGRESS — SUBMISSION NOT READY.**
The supported application has prior local and Nebius/Tavily acceptance evidence.
Current results, exact artifact identity and external blockers are recorded in
[the release report](docs/RELEASE_REPORT.md). GitHub token authentication is verified;
complete live workflows still need a selected disposable repository.

## Capability status

| Capability | Implemented and locally tested | Live evidence |
|---|---|---|
| Owner bootstrap/login/logout; session revocation | Yes | Local API and browser |
| Memory CRUD/search/export and new-session recall | Yes | PostgreSQL + real Nebius recall |
| NVIDIA inference and validated tool loop | Yes | Nebius Nemotron model, bounded live evaluation |
| Engineering briefing with citations and saved note | Yes | Full live skill blocked by GitHub; Tavily search verified |
| Research to action: edit, approve, create, confirm issue | Yes | Controlled transport only; live write pending |
| Follow-through and durable schedules | Yes | Separate worker + local note effects |
| Cancel, lease recovery, uncertain-write reconciliation | Yes | Failure injection; no live GitHub timeout test |
| Connections: scope, test, expiry, replace, revoke | Yes | Nebius/Tavily/workspace; GitHub workflow pending |
| Responsive Assistant, Memory, Skills, Settings, Activity | Yes | Chromium desktop/tablet/mobile and accessibility checks |

Owner model/limit settings persist in PostgreSQL, with revision checks and operator
ceilings. See [settings contracts](docs/SETTINGS.md), [HTTPS operations](docs/OPERATIONS.md),
and the [current verification and remaining work](docs/RELEASE_REPORT.md).

## Start locally

Requires Git, Docker with Compose v2, and uv (tested 0.13.1). Containers build with
Node 22 and Python 3.13 and use PostgreSQL 17; dependencies are locked. A native
frontend development environment needs Node 22.12 or newer within Node 22.

```sh
# Fresh installation only; preserve an existing .env.
cp env.release.example .env
./scripts/start.sh
```

Open http://localhost:8000. Read the generated bootstrap token locally from
`.env.runtime` and choose your own owner password. The script preserves `.env`,
generates missing runtime secrets and starts the API, database and worker.
On this host, Docker is a Podman wrapper; start its API socket with
`systemctl --user start podman.socket` if necessary.

In Settings → Connections, import configured server credentials or enter them directly.
Test Nebius, enable workspace, select one GitHub repository and set Tavily research
domains. Save a preference in Memory, then run a skill. Unconfigured integrations
show errors; the release never substitutes sample completions.

- `NEBIUS_API_KEY`: real Token Factory key. Default endpoint is
  `https://api.tokenfactory.nebius.com/v1`; model is
  `nvidia/nemotron-3-super-120b-a12b`. Legacy `MODEL_ID` is supported.
- `GITHUB_TOKEN` and `GITHUB_REPOSITORY=owner/repository`: selected repository
  metadata/issues read access, and Issues write for an explicitly approved issue.
- `TAVILY_API_KEY`: real search key; choose approved domains in Settings → Connections.
- `.env.runtime`: generated encryption key, bootstrap token and Compose database
  password. Keep this file private and backed up separately from the database.

## Verify

```sh
# PostgreSQL 17 binaries installed locally; creates a separate loopback test cluster.
./scripts/test_db.sh
# Use the URL printed by that script and Node 22 on PATH.
TEST_DATABASE_URL=postgresql://watcher@127.0.0.1:55432/postgres ./scripts/verify.sh
```

On a new machine replace `watcher` with the printed database username. Install
Chromium once with `cd frontend && npx playwright install chromium` after npm
installation. The verification script runs formatting, lint, types, PostgreSQL
integration tests, coverage, production build, browser workflows, dependency
checks and a configured-secret scan. Controlled vendor transports are test-only.

Additional checks:

```sh
uv run python -m scripts.clean_release_smoke
TEST_DATABASE_URL=postgresql://watcher@127.0.0.1:55432/postgres uv run python -m scripts.backup_smoke
# Real Nebius usage; requires a working key and incurs provider usage:
uv run python -m scripts.live_smoke
TEST_DATABASE_URL=postgresql://watcher@127.0.0.1:55432/postgres uv run python -m scripts.evaluate_live
```

The clean smoke builds a secret-free source snapshot, starts an isolated Compose
project on port 8002 and removes only that disposable project's volumes. The
backup drill requires permission to create temporary test databases. Live checks
use fictional tasks and perform no GitHub writes.

## Privacy and operating limits

PostgreSQL and notes are owner-controlled. Selected memory/context is sent to
Nebius; search queries go to Tavily; approved issue content goes to GitHub.
This is not local-only inference or end-to-end encryption. Provider credentials
are encrypted at rest with a separate key. Deletion removes active application
records; retained conversation copies, files and backups need their own deletion
or retention policy. See [privacy](docs/PRIVACY.md).

The worker must remain running for schedules. Intervals are elapsed UTC durations;
missed occurrences coalesce. External writes require an exact approval, can become
uncertain after a lost response, and are reconciled without blind retries.
Cancellation cannot undo completed effects. Currency cost stays unknown unless
verified pricing is configured. HTTPS and secure cookies are required for a
remote production deployment.

[Operations](docs/OPERATIONS.md) covers backups, restore, upgrades and legacy import.
[Architecture](docs/ARCHITECTURE.md), [traceability](docs/TRACEABILITY.md),
[threat model](docs/THREAT_MODEL.md), [release evidence](docs/RELEASE_REPORT.md) and
[ECC setup](docs/ECC_SETUP.md) record the implementation and evidence.
[Judge guide](docs/JUDGE_GUIDE.md), [demo script](docs/DEMO_SCRIPT.md),
[changes](docs/HACKATHON_CHANGES.md), [feedback](docs/FEEDBACK.md) and
[release acceptance](docs/RELEASE_REPORT.md) prepare the submission package.
No hosted demo, public video or submitted entry is claimed.

Original project: https://github.com/RafalW3bCraft/TheCommander. MIT license and
existing authorship are preserved; see [LICENSE](LICENSE) and
[THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES).

## Exported test build

`uv run python -m scripts.package_release` writes a source archive under
`.runtime/releases/` and a SHA256 manifest in `docs/evidence/release-manifest.json`.
It excludes private environments, databases, notes, Git history, ECC catalogs and
legacy runtime code. The archive starts with the same `./scripts/start.sh` path.
For source-inventory and verification scripts in an extracted archive, initialize
a local index **before creating private configuration**:

```sh
git init
git add .
```

The archive includes `.gitignore` to keep later private configuration out of the
index. This creates no remote repository and publishes nothing. Run the documented
verification checks and keep live integration results separate from fixtures.
