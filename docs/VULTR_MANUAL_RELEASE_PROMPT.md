# TheCommander / Vultr: manual configuration and release completion

You are working in RafalW3bCraft/TheCommander. Complete the remaining release work using this loop:
ANALYZE → ITERATE → PLAN → VERIFY PLAN → BUILD/FIX → TEST → VERIFY EVIDENCE → ANALYZE AGAIN.

This is an execution task, not merely a request for another plan. Work until every independently completable gate is satisfied; if a real account, credential, deployment budget or human approval is missing, state the exact missing item and continue other authorized work. Preserve source structure, existing capabilities, keys and data. No frontier-model intelligence parity is claimed.

## Non-negotiable Git and preservation rules

- The only permitted working/push branch is the existing `vultr`. Never checkout, commit to, merge into, reset, rebase or push `main` or any other branch. Do not create alternate branches or force-push. Before every commit/push assert `git branch --show-current` equals `vultr`.
- Inspect `git status` first; preserve unrelated changes. Fetch the current remote and fast-forward `vultr` only if safe. Do not assume the old local pre-publication bundle history is the remote history.
- Record the current `vultr` SHA and read the `main` ref only as a before/after non-mutation check. Do not write it.
- Read applicable AGENTS.md plus `docs/VULTR_ENV_SETUP.md`, `docs/VULTR_PLAN.md`, `docs/VULTR_GUIDE.md`, `docs/VULTR_VERIFICATION.md`, `docs/VULTR_CODEX_PROMPT.md` and current CI logs. Older local-only verification is historical, not the latest CI outcome.
- Preserve private .env files and existing encryption/bootstrap/database/provider keys. No credential rotation, wholesale .env replacement, database reset, volume deletion, destructive migration or feature removal.
- Keep the existing FastAPI/React/PostgreSQL/worker/memory architecture. Prefer small additive fixes over replatforming or optional feature expansion.

## Known starting evidence — verify afresh before acting

Published implementation: `f5a90fa88611cff0c27cf9bc539ac5cadc38be0d` on `vultr`.
- Release run https://github.com/RafalW3bCraft/TheCommander/actions/runs/41971716067 failed overall, but its real PostgreSQL Python suite passed 174 tests, skipped 3 explicit container tests and reached 90.44% coverage. Type/lint/production build also passed. Browser suite passed 10/11; `memory recall explains disabled and degraded index states` failed inside the login helper waiting for the Project combobox.
- Containment run https://github.com/RafalW3bCraft/TheCommander/actions/runs/41971716172 failed building Dockerfile.egress because the root `.dockerignore` allowlist excluded `deploy/sandbox/proxy.py`. Real sandbox tests did not run.
- Live Vultr inference, live vision, gVisor execution and a public production deployment have not been established by those results.
- Previously observed development dependency findings require a fresh audit; do not freeze a stale count or use force updates blindly.

## Phase 1 — Analyze and repair CI before deployment

1. Pull exact current logs and reproduce each remaining failure. Publish a short ordered repair plan and acceptance checks, then execute it.
2. Fix Docker build context with narrowly scoped inclusion of the required public browser/proxy sources. Preserve exclusions of .env variants, private runtime state, .git, credentials and caches. Verify BOTH image builds; do not broaden the context to the entire repository.
3. Diagnose the memory browser regression using trace/screenshot, console errors, authentication/rate limits, fixture state and request timing. The failure is that the Project combobox was absent after login; its cause is not established. Prioritize checking the shared login-IP rate bucket: the suite now runs 11 tests in about 45 seconds and the production login limit defaults to 10/minute. Treat this as a hypothesis until the actual response/trace confirms it; fix test isolation rather than weakening production authentication. Do not assume the selector is wrong, weaken assertions, disable the test, bypass auth, increase waits blindly or share sessions to conceal a defect.
4. Complete Ruff, format, mypy, PostgreSQL 17 integration/coverage, frontend type/build/lint/format and the full real-API browser suite. Preserve coverage at or above the existing 80% requirement; never lower a threshold to manufacture green CI.
5. Audit Python, memory-service and Node dependencies. Fix compatible security updates with meaningful regression checks; document remaining findings honestly. Regenerate OpenAPI/types only through existing scripts.
6. Commit focused changes to `vultr`, push only `HEAD:refs/heads/vultr`, inspect actual Actions results and iterate until both workflows are green. A queued run is not a pass; runc in CI does not establish the gVisor deployment gate.

## Phase 2 — Manually configure real keys without disclosure

1. Inventory recognized setting names from `commander/settings.py`, Compose files and the memory-service process. Report only configured/missing status and conflicting KEY NAMES. Never print values or complete environment files. Do not put a secret in this prompt, an API-tool argument visible in chat, command-line URL, test fixture, screenshot, Git commit or evidence log.
2. For a fresh installation with no old data, create only missing .env from the example and use `scripts/setup_runtime.py` to generate .env.runtime. For an existing installation preserve/recover its ORIGINAL encryption/bootstrap/database secrets before starting. Backups must remain protected and untracked. Do not regenerate missing encryption keys against an existing encrypted database.
3. Ask the human to enter real provider secrets in a local editor or a hidden terminal prompt outside the model-visible transcript. Do not ask them to paste keys into chat. Never echo a key to confirm it. You may use the configured values through the application's authorized code paths for tests.
4. Required Vultr fields: VULTR_API_KEY must be the Serverless Inference subscription key. Discover the authenticated model list; select/verify actual IDs for PROVIDER_MODEL, SANDBOX_MODEL and SANDBOX_VISION_MODEL. Do not invent model names or infer vision support from listing alone. Vultr endpoint is fixed at https://api.vultrinference.com/v1; do not introduce ignored alternate names such as VULTR_MODEL or VULTR_BASE_URL.
5. Retain existing Nebius/OpenAI/Anthropic/Tavily/GitHub credentials and defaults outside the demo. Set INFERENCE_PROVIDER=vultr for the new demo configuration and explicitly select Vultr for the demo owner. Confirm current owner preferences, saved connection credential, and new run snapshots; .env defaults do not overwrite them. Do not migrate/rewrite old run records or unrelated schedules to change history.
6. Configure only the single selected GitHub repository and approved Tavily domains through Connections. Keep runtime app token scopes limited to its needs; use separate authenticated coding-agent Git access for source/workflow pushes. .env GITHUB_TOKEN does not automatically authenticate terminal git.
7. Respect loader precedence: process environment overrides .env.runtime, which overrides .env. Compose environment overrides its service env files; CLI --env-file handles interpolation separately. Use both --env-file .env and --env-file .env.runtime for the documented overlays. APP_ORIGIN auto-created in .env.runtime can override a newer value in .env.
8. Match DATABASE_URL to execution location: API/ordinary worker use db:5432 inside Compose; same-host native sandbox worker uses the opt-in loopback DB port 5434 and existing password. A separate VM needs the real private-network URI and TLS. Use the same schema and encryption key; never dump a full credential-bearing URI to logs.
9. Initially SANDBOX_ENABLED=false; SANDBOX_RUNTIME=runsc; exact JSON public-domain allowlist; prebuilt trusted browser/proxy images; resource limits unchanged. Enable product execution only after actual containment tests pass.
10. Validate numeric ranges, JSON domain lists, file permissions and unsupported/duplicate setting names. Optional numeric caps must be omitted rather than empty strings. Preserve existing spend caps: sandbox inference clears inherited provider prices, so a strict cap with unknown Vultr prices must remain blocked or be correctly implemented with verified model-specific accounting. Do not silently disable budgets or reuse old model prices.
11. Import missing credentials through authenticated Settings → Connections. The import flow does not replace existing saved, revoked or expired records; update/test such a connection explicitly in its form. Recreate affected services when their environment changes. Do not authorize sensitive actions by directly mutating approval rows.

## Phase 3 — Real execution on the authorized Vultr runner

- Use existing authorized Vultr infrastructure. If new billable infrastructure is needed, collect the missing target/account/region/budget decision once and prepare a concrete deployment plan before provisioning. Do not assume credits mean unlimited usage.
- Install/verify Docker Engine 28+ and gVisor. Keep runsc mandatory; verify the runner uses the intended local Unix socket. API containers receive no Docker socket. No privileged containers, host mounts/networking, inherited credentials, Chromium sandbox disabling, or fallback host code execution.
- Build trusted browser and gateway images from the fixed contexts; pre-pull the exact configured pinned Python image because the runner uses --pull=never. Confirm the browser package/base-image version match and namespace/seccomp compatibility on that VM.
- Run the existing preflight and known 42 probe. Inspect Docker's actual enforced configuration and destroyed-container receipt.
- Run real container tests with RUN_SANDBOX_DOCKER=1 RUN_SANDBOX_BROWSER=1 SANDBOX_TEST_RUNTIME=runsc. Distinguish skipped tests, mocks, runc CI and actual gVisor evidence.
- Verify network-none Python, no secret inheritance, denied host-root writes, time/memory/PID/output caps, container reset/destruction, crash cleanup and separation between tasks. Browser networking must be internal with isolated gateway mode (ordinary --internal can expose bridge-address host services), exact allowed public HTTPS destinations, public-only/mixed-answer DNS checks and pinned peers. Test private/metadata targets, unapproved redirects, websockets/downloads/popups and direct-egress denial.
- Verify control-plane cancellation, lease recovery, duplicate decisions, approval expiry, denial, changed plan/domain/runtime/observed URL/page fingerprint, owner/project boundaries and uncertain external effects. No blind retry of a partially completed browser write.

## Phase 4 — Real Vultr inference and full product flows

1. Verify account model discovery, a real text response, structured JSON planning, tool-call capability where the normal assistant needs it, genuine screenshot/image input to the selected vision model, and usage reporting. Keep provider headers and secrets out of evidence. A fixture or a provider fallback is not proof.
2. Code flow: user goal with independently known expected answer → Vultr-generated Python → gVisor container output → bounded repair on a real code error → explanation/verification → UI receipt/export. Capture sanitized task ID, model, output, exit code, image/runtime/resource receipt and cleanup.
3. Browser flow on an operator-controlled public HTTPS form using fictional data: initial observation/screenshot → real vision check → inspect exact fill/click plan → human password confirmation and explicit approval → fresh sandbox/page and URL/hash revalidation before effects → final screenshot and real vision result. The human approves; do not auto-approve on their behalf. Confirm the original approval snapshot remains inspectable after completion/failure.
4. Read-only browser success must verify the actual user's goal, not just that any page appeared. Show failed/uncertain verification honestly.
5. Rerun original memory, projects, sessions/revocation, schedules, research and approved GitHub issue behavior with configured providers. External writes still need the app's real human approval. Treat prior live evidence as historical unless rechecked.

## Phase 5 — Production deployment and submission package

- Use the existing deployment architecture/HTTPS overlay, actual DNS, correct APP_DOMAIN and matching HTTPS APP_ORIGIN with PRODUCTION=true in each effective process configuration. The generated runtime origin must not shadow the intended HTTPS value on the host worker.
- Configure the existing systemd runner with a protected EnvironmentFile and the correct native/private DB URL. Verify readiness/heartbeat after a restart. Never expose database or Docker ports publicly. Test restore with separate disposable resources without deleting user data.
- Run responsive desktop/mobile and accessibility checks against the deployed app. Keep public demo data fictional, real owner/bootstrap credentials private and the service available for judge access by an agreed method.
- Update truthful README architecture, actual Vultr services, exact branch/commit, setup commands, model/key status and current CI/live evidence. Preserve old dated evidence rather than overwriting it as if it came from this run.
- Confirm existing-project eligibility with organizers; neither earlier public brief/rule-book research established an explicit ruling. Disclose the old baseline and new hackathon work; do not rewrite history to imply a fresh project.
- Prepare a genuine ≤5-minute video within the actual current form's size limit, PDF slides, 16:9 cover, public demo URL, public vultr commit/branch URL and final descriptions/tags. Demonstrate both execution patterns and a real containment moment.
- Do not claim entry submission, eligibility approval, successful inference or a deployed URL without actual confirmation. Submit to LabLab only within the user's applicable submission authorization; never silently accept rules or human action approvals as part of testing.

## Required final report

Report branch and exact published commit; confirmation that main stayed unchanged; configuration KEY NAMES/status only; defects fixed; actual tests/coverage and Actions URLs; Docker/runc/gVisor/live-Vultr distinctions; deployed URL if established; sanitized task/receipt evidence; unpassed release gates; and the exact next human action for a genuine external blocker. Label production-ready and submission-ready separately, only after their corresponding checks actually pass.

Do not stop with “should work.” Build, inspect the output, fix the failure, and verify again until the work is complete or a specific external dependency prevents progress.
