# Release report — 2026-10-23

**IMPLEMENTATION COMPLETE — LIVE VERIFICATION PENDING.**

The locally implementable release is integrated and verified. GitHub live read,
issue creation and provider receipt verification remain blocked by missing token,
repository scope and explicit live-write authority. No remote deployment,
publication, video upload or hackathon submission was performed.

## Scope and preserved work

Release 0.2.0 on `rebuild/personal-ai`, based on historical `e4912469` and preserved
user checkpoints `37e4fa4`, `f2379a7`, `9e84075`, plus the final working-tree diff.
Both instruction documents were read fully. The private `.env`, existing
`env.example`, `schema.sql`, legacy modules, MIT authorship and existing public
SQL tables were preserved. The prior README is retained as LEGACY_README.md.
No commit, reset, push or third-party resource change was performed by this run.

The release uses `commander/` FastAPI services, PostgreSQL schema migrations,
`frontend/` React/TypeScript and a separate worker. OpenAPI generates frontend
types. Core features include secure owner sessions, durable conversations and
recall, memory correction/deletion/export, encrypted scoped connections, three
skills, exact GitHub approval, persistent notes, schedules, cancellation, recovery,
uncertain-write reconciliation and visible evidence/receipts.

ECC 2.2.3 source is pinned at `90606c8315ee09cafc303515c5f33024db6b9882`.
The supported project-local adaptation exposes the full catalog under ignored
.tools/ecc. Native Codex installation/hooks are not claimed; see ECC_SETUP.md.
An independent security review supplied six findings, fixed with regression tests.
Other review work was performed by the primary agent; browser delegation did not
complete, and no independent browser sign-off is claimed.

## Verification results

| Gate | Actual result | Evidence |
|---|---|---|
| Ruff lint/format and mypy | Passed | evidence/final-verification.txt |
| PostgreSQL integration/contracts/security/recovery | 42 passed | evidence/final-verification.txt |
| First-party Python coverage | 89.63%; required minimum 80% | evidence/final-verification.txt; EVALUATION.md scope |
| OpenAPI types, frontend format/lint, tsc/Vite production build | Passed | evidence/final-verification.txt |
| Chromium desktop/mobile | 2 scenario suites passed; zero axe violations on checked screens | evidence/browser-results.json |
| Visual review | Opened desktop and 375px mobile screenshots; readable controls, visible focus, no horizontal overflow | evidence/browser-desktop.png; browser-mobile.png |
| Python/npm dependency audit | No known vulnerabilities reported | evidence/final-verification.txt |
| Configured-secret scan | No configured private values in tracked/unignored files or built frontend | evidence/final-verification.txt |
| Container build and actual API/worker/PG startup | Passed; readiness and worker heartbeat observed | evidence/compose-build.txt; compose-smoke.json |
| Clean-source startup script | Passed from copied source without host dependencies/private env; fresh volumes/secrets | evidence/clean-release-build.txt; clean-release-smoke.json |
| Backup/restore | Memory/revision and encrypted credential restored; notes archive content preserved | evidence/backup-restore.json |

Canonical command executed:
`TEST_DATABASE_URL=postgresql://watcher@127.0.0.1:55432/postgres ./scripts/verify.sh`,
with installed Node 22.23.3 selected on PATH for the final run. Python was 3.13.5;
PostgreSQL tests use 17.10. The earlier default Node 20 run passed but emitted an
engine warning; Node 22 is now declared and used. One Starlette/httpx TestClient
deprecation warning and an ESLint 9 maintenance warning remain; neither was hidden.
Remote CI is configured but has not run because this work was not pushed.

Additional executed commands: `./scripts/test_db.sh`,
`uv run python -m scripts.clean_release_smoke`,
`TEST_DATABASE_URL=... uv run python -m scripts.backup_smoke`,
`uv run python -m scripts.compose_smoke`,
`uv run python -m scripts.live_smoke`,
`TEST_DATABASE_URL=... uv run python -m scripts.evaluate_live`, and
`TEST_DATABASE_URL=... uv run python -m scripts.live_research_smoke`.
Compose was built with `docker compose -p thecommander-releasecheck --env-file
.env.runtime up --build -d`. Test schemas/databases are isolated from user data.

The clean test is a working-source snapshot (including uncommitted release files),
not a claim that a published commit has been cloned by a third party. Container
layers may be cached; host node_modules and virtual environments are excluded.
The unique cleancheck project and its disposable volumes were removed afterward.
The releasecheck project is stopped at handoff, with its volumes preserved, so
port 8000 is available for the documented startup.

## Connector evidence

| Connector | Implementation | Deterministic checks | Live evidence |
|---|---|---|---|
| Nebius | Model discovery, inference, validated tools, budgets/errors | Passed | Real NVIDIA model list/tool roundtrip and evaluation |
| Tavily | Scoped search and persisted URL/excerpt/time | Passed | Validation + broker search; five docs.python.org results |
| GitHub | Repository read, exact issue preview/approval/create/GET confirmation, uncertain reconciliation | Passed with controlled HTTP transport | Not run: missing token/repository/write authority |
| Workspace | Owner-scoped safe Markdown create/read/list and receipt/recovery | Passed | Real file effects in Compose and live model evaluation |

Nebius endpoint `api.tokenfactory.nebius.com`; exact model
`nvidia/nemotron-3-super-120b-a12b`. Evaluation: 30/30 acceptance scenarios passed,
26 reaching inference, 29 calls, 27,976 reported tokens, median task latency 3,844 ms,
maximum 7,959 ms. Four cases deliberately checked pre-inference cancel/disconnect.
Repeated recall and bounded-output checks are not a broad model-quality benchmark.
Recovery and uncertainty are separately tested with failure injection. Prices and
currency costs remain unknown. Full details and limits are in EVALUATION.md.

Tavily live smoke occurred at 12:15 UTC on October 23. The broker search took
3,461 ms and persisted five evidence rows. The full engineering-briefing and
research-to-action live workflows remain blocked by GitHub; their complete
frontend-to-backend paths passed with explicitly controlled vendor responses.
Browser fixtures are not evidence of external provider success.

## Exact remaining dependencies

- `GITHUB_TOKEN` is a placeholder. Supply a real fine-grained token restricted to
  one selected repository: metadata/read and Issues read, plus Issues write for
  creation. `GITHUB_REPOSITORY` is currently absent. Specify a disposable
  `owner/repository` and explicitly authorize the live issue creation/verification.
  Then run repository validation, briefing, research-to-action approval/create/GET
  confirmation, open the real receipt and check persisted activity after restart.
- `TAVILY_API_KEY` and `NEBIUS_API_KEY` are present and live-verified. Choose the
  intended production research domains in Connections; the smoke used only
  docs.python.org. Current evidence does not validate arbitrary domain choices.
- Legacy `SESSION_SECRET` is a placeholder but is not used by this release.
  Generated `ENCRYPTION_KEY`, `BOOTSTRAP_TOKEN` and `POSTGRES_PASSWORD` are present
  in private .env.runtime. Preserve them; do not replace working keys casually.
- Remote hosting, HTTPS/domain, judge access and sustained availability are not
  configured or tested. The original development DB at port 5433 was not restarted;
  canonical Compose startup uses its own database and named volumes.

No live GitHub issue, GitHub write-timeout exercise, remote HTTPS/browser test,
load/endurance benchmark, remote CI run, or independent penetration test was done.
No unresolved critical/high finding is known from the performed review; this is
not an absolute-security guarantee.

## Startup, privacy and submission

Run `./scripts/start.sh`, then open http://localhost:8000 and bootstrap using the
local .env.runtime token. See README and OPERATIONS.md for prerequisites, test
setup, backups, production HTTPS, key management and safe legacy import.

Memory storage is owner-controlled; selected context goes to Nebius, queries to
Tavily, and approved issue content to GitHub. Credentials are encrypted at rest.
Processing is neither local-only nor end-to-end encrypted. Deleting a memory does
not erase copies in prior messages, files or backups. See PRIVACY.md.

README, architecture/spec/threat model, traceability, evaluation, operations,
changes/provenance, judge guide, 2:50 demo script, feedback, MIT license and notices
are prepared locally. Recording, public YouTube URL, publication of final code,
hosted judge access and actual submission remain pending. Official
[rules](https://nebiusglobalaihackathon.devpost.com/rules) and
[FAQ](https://nebiusglobalaihackathon.devpost.com/details/faqs) were rechecked on
2026-10-23: deadline 2026-10-30 17:00 UTC; maintain testing availability through
2026-12-15. No organizer acceptance or eligibility guarantee is made.
