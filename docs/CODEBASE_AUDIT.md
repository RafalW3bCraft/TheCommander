# Recursive codebase audit — 2026-10-24

Production audit: **68/100, internal beta only**, because the GitHub-dependent
live path, remote HTTPS deployment and remote CI evidence are still missing.
This ordinal score is engineering triage, not a probability or certification.
Local implementation and regression evidence are recorded below; do not interpret
controlled provider responses as live integration verification.

## Scope and inventory

The reproducible [recursive inventory](evidence/recursive-inventory.json) enumerates
every tracked and unignored file, including the entire `.agents` catalog. It
records classification, hashes, all first-party Python imports and route handlers,
dependency manifests and identical nonempty source files. The initial pass parsed
54 Python modules and found 39 explicit HTTP handlers. Generated evidence changes
the file count; the JSON artifact is authoritative for the current snapshot.

Reviewed release source, tests, scripts, migrations, frontend, lockfiles, container
and CI configuration, documentation and legacy entrypoints. Legacy Python syntax
and import/definition structure were inspected without importing or executing its
shell and network tools. No duplicate nonempty first-party source file was found;
the two user instruction documents now differ because the owner expanded the plan.

Ignored dependencies/caches, Git objects, private environment files, runtime
databases/notes and the pinned ECC checkout are separate boundaries. Dependency
lockfiles and vulnerability audits cover installed packages; this is not a
line-by-line audit of third-party implementations. ECC files are fully inventoried
for provenance/applicability, not individually certified for quality or safety.

| Directory/surface | Wiring and decision |
|---|---|
| `commander/` | Supported API → authenticated domain services → owner-scoped PostgreSQL, constrained providers and workspace; retained |
| `commander/migrations/` | Transactional versioned 001–003; new tables isolated from legacy public data; retained and upgrade-tested |
| `frontend/src/` | Five views → common CSRF/error client → generated OpenAPI types; no frontend vendor credentials |
| `tests/`, `frontend/e2e/` | Real PostgreSQL and browser workflows with explicitly controlled vendor transport; retained |
| `scripts/` | Setup, gates, live evaluation, backup and clean startup drills; separate from production image |
| Root Python, `agents/`, `templates/`, `static/` | Historical implementation; shell/HTTP/fallback behavior is outside release authority. Preserved, unserved and unpackaged |
| `legacy/` | Exact old root entrypoint archived; new `main.py` launches only supported API; ADR 002 |
| `requirements.txt`, `schema.sql`, `env.example` | Historical setup/data references; preserved. Release uses `pyproject.toml`, `uv.lock`, npm lock and `env.release.example` |
| `.agents/` | Owner-managed ECC 2.2.0 full catalog; all 276 skills/693 artifacts inventoried; not production dependencies |
| `.tools/ecc` | Ignored pinned ECC 2.2.3 reference; not native host plugin/hooks |
| Docker/Compose/CI | Single locked API/frontend image, separate worker and PostgreSQL, loopback binding, nonroot runtime, health checks and volumes |
| `docs/` | Requirements, decisions, threat model, provenance, evidence, release operations and audit reports; linked from ECC ledger |

## Defects fixed

| Severity | Finding and fix | Evidence |
|---|---|---|
| High | Future queued conversation prompts entered earlier context. Migration 003 associates messages with runs; context cutoff and role ordering preserve turn boundaries | `test_queued_conversation_context_excludes_future_turns` |
| High | Unknown skills inherited conversation tools and stale queued definitions could execute. Unknown IDs now fail closed; execution checks recorded definition hash | Unknown/stale skill regressions |
| High | Disabled connections remained usable in dispatch; malformed validation could mark a connection valid. Enforce enabled/expiry/revocation and provider shape/resource identity | Disabled/malformed validation regressions |
| High | A saved note followed by model failure could lose its recovery path. Durable intent makes failure uncertain; cancelled runs retain read-only note reconciliation | Note effect/failure/cancel regression |
| Medium | Issue proposals could contain unsupported citations. Reuse evidence URL validation before proposals and final text | Invented proposal citation regression |
| Medium | Runtime validation could echo private values. Hide Pydantic settings input values | Runtime secret-error regression |
| Medium | Environment import overwrote existing connection scopes or revived revoked state. Import only missing records | Environment import regression |
| Medium | Conversation deletion raced enqueue; cancellation transitions were split. Lock the conversation and transact run/action/event changes | Workflow regression suite and route review |
| Medium | Recovery retained stale failure text after success. Clear error on successful completion | Retry recovery regression |
| Medium | Memory, run detail and note requests could overwrite newer UI state. Guard response ordering, count pending operations and clear deleted editors | CP01–CP05 and delayed-response browser scenario |
| Medium | Root startup could launch obsolete command routes. Archive original bytes and provide supported launcher | Legacy-route regression; ADR 002 |
| Low | Invalid note filename became server error; ancillary API responses lacked explicit contracts; memory expiry and budget data were not fully wired | Path validation, response models/generated types, browser memory expiry and visible usage |
| Low | Frontend effects and configs escaped full lint/type scope. Stable callbacks and hook rules now cover source, browser tests and configuration | Format/lint/tsc/Vite gates |

Removed the duplicate unused engine budget implementation and redundant request
body check; retained the shared inference budget and streamed-size boundary.
No speculative deletion of legacy code or user-installed ECC files was performed.
Previous security/operational findings F01–F13 remain in [FINDINGS.md](FINDINGS.md).

## End-to-end and evidence boundaries

[Click-path audit](CLICK_PATH_AUDIT.md) traces controls/state/routes;
[traceability](TRACEABILITY.md) maps requirements to services and tests;
[twelve-layer agent audit](evidence/agent-architecture-audit.json) maps prompt,
memory, tool, rendering and persistence behavior. These complement the recursive
inventory rather than treating file enumeration as proof of correctness.

Run `./scripts/test_db.sh`, then `TEST_DATABASE_URL=... ./scripts/verify.sh`
with Node 22 on PATH. [Audit verification](evidence/audit-verification.txt) records
the actual results. [Browser JSON](evidence/browser-results.json) records scenarios
and durations; screenshots cover 1440px desktop, 768px tablet and 375px mobile.
Zero axe findings on tested screens does not establish full WCAG conformance.
Keyboard checks were performed; no full screen-reader pass or Core Web Vitals
measurement was performed. Visual regression verdict is **INCONCLUSIVE** because
there is no committed, approved screenshot baseline for the final UI.

Live Nebius and Tavily evidence is separately dated in [EVALUATION.md](EVALUATION.md).
Fresh-source Compose startup, retained-volume upgrade and backup/restore checks
are recorded in the release report. Provider outages, uncertain writes and
permission races use deterministic failure injection; no live GitHub write was
performed. Cancellation stops future authorized dispatch after acquiring the
owner lock; it does not abort or undo an already dispatched provider operation.
Network timeouts and step budgets are bounds at dispatch/checkpoints, not a
hard real-time process kill guarantee.

## Remaining release blockers and limitations

- Real `GITHUB_TOKEN` restricted to a disposable repository, `GITHUB_REPOSITORY`,
  and explicit live issue-write test authority are missing. Full live briefing
  and research-to-action workflows cannot be certified without these.
- Remote HTTPS deployment, judge access, sustained uptime, remote CI, load tests,
  large-table migration testing and independent penetration testing are unverified.
- Starlette TestClient/httpx deprecation and ESLint 9 maintenance warnings remain
  visible. Locked dependency audit results are point-in-time evidence.
- Legacy modules intentionally remain unsupported; they have not been made safe
  for standalone execution. Do not reconnect them to the release API.

Next dependent action: configure the selected GitHub repository and scoped token,
then run the explicitly authorized approval → creation → GET-confirmed receipt
path. Local code, reviewable artifacts and repeatable gates are prepared first.
