# Codex continuation / release prompt

Work in RafalW3bCraft/TheCommander on the existing branch `vultr` ONLY. The user has authorized additive implementation, debugging and testing. Do not change branches, merge, rewrite history, delete existing capabilities, rename/remove old environment keys, rotate existing keys or overwrite private configuration. Read repository instructions and `docs/VULTR_PLAN.md`, `docs/VULTR_GUIDE.md`, `docs/VULTR_VERIFICATION.md` first. Inspect `git status`, record the current commit and preserve unrelated work.

Objective: finish a demonstrably functional Blast Radius Zero submission with both sandboxed Python and sandboxed Playwright, using Vultr as the control plane and Vultr Serverless Inference for all agent planning/verification. Preserve the current FastAPI/React/PostgreSQL/memory structure. Do not interpret frontier-model product ambition as evidence that intelligence parity exists.

Follow this loop for every change: analyze current evidence → identify a concrete failed gate → write a bounded plan → verify the plan against rules/security/compatibility → implement the smallest complete change → test actual behavior and negative paths → inspect results → iterate. Keep Git commits coherent and restricted to `vultr`. Do not claim a test pass based on mocked transport/container results or a skipped test.

First verify local/CI findings recorded in VULTR_VERIFICATION. Fix implementation/CI defects before optional features. Audit:
- `commander/sandbox/contracts.py`, `service.py`, `worker.py`, `runner.py` and migration 010;
- trusted `deploy/sandbox/browser.py` and CONNECT proxy;
- the Sandbox UI, exact approval/reauthentication and project history;
- Vultr provider routing, fixed endpoint, usage reservations and model discovery;
- the existing source/schema/keys/defaults and legacy workflows for regressions.

Release gates, in order:
1. Ruff, mypy, production frontend build/lint/format, full PostgreSQL 17 test suite/coverage, existing browser regressions, sandbox UI test, dependency audits and configured-secret scan. Keep old evidence files intact; write new, dated evidence.
2. On an actual Vultr runner with Docker/gVisor, build browser and gateway images. Run `scripts.sandbox_preflight` then the explicit probe. Run real code/browser tests with RUN_SANDBOX_DOCKER=1 and RUN_SANDBOX_BROWSER=1, keeping SANDBOX_RUNTIME=runsc. The runc CI pass is not the gVisor deployment gate. Never enable privilege, mount host directories, inherit proxy/API credentials or disable Chromium sandbox to get green tests.
3. Demonstrate no network for Python, no inherited credentials, denied host-root writes, timeout/output cap, cleanup, per-task separation, gateway denial of private/metadata/mixed DNS targets and unapproved redirects. Verify orphan cleanup after runner interruption. Inspect Docker's actual enforced config, not just generated flags.
4. Configure the owner's encrypted Vultr connection through existing Settings/import. Read the authenticated model list, choose available text and vision-capable IDs, and execute real requests. No fallback to Nebius/OpenAI/Anthropic for Sandbox. Save sanitized usage/model/task receipts; never log credentials. Preserve strict cost/budget failures rather than silently disabling caps.
5. Perform an end-to-end code goal: model writes Python, container prints correct output, verifier explains it, UI shows receipt. Use an independently known expected result.
6. Perform a controlled public-HTTPS browser form workflow: screenshot observation, real vision check, inspect every proposed selector/value/target, exact expiring human approval, fresh-page revalidation before actions, new disposable container, final screenshot and vision check. Test denial, expiry, tampered plan/domain/runtime digest, duplicate approvals, logout/revocation, cancellation and uncertain external effects without replay. Use public fictional data; no payments/secrets. Do not approve actions automatically on behalf of a user.
7. Verify public HTTPS deployment on Vultr, browser responsiveness/accessibility, database restore and original memory/research/GitHub workflow behavior. The API must not get a Docker socket. Keep the runner's database/control authority separate from untrusted execution.
8. Update README with exact deployed Vultr services/architecture and truthful capability status. Record pre-existing baseline/new work and organizer eligibility confirmation. Do not claim existing-project eligibility until explicitly established.
9. Prepare a ≤5-minute genuine demo, PDF slides, 16:9 cover, public branch/commit URL and live app URL. Show a real containment moment and both execution patterns. Fill the actual LabLab limits, and submit only within user authorization for that external submission. Do not fabricate a URL, screenshot, successful inference, video or confirmation.

If cloud/account access is missing, complete all code/tests/runbooks independently, identify the exact missing credential/infrastructure gate and leave a reproducible command/task sequence. Do not stop at a plan when an implementation or repair can still be completed. Do not deploy billable infrastructure without the user's applicable deployment authorization and budget.

After the mandatory gates pass, consider only evidenced improvements from the roadmap: safer artifact handling and diff review, unified streaming, capability-aware model selection, retrieval evaluations, operator monitoring and tenant isolation. Do not add a second agent framework or replatform the application just to expand feature count.

Final report must list exact branch/commit, files/behavior changed, actual test results with evidence locations, deployed URLs if any, live-vs-fixture status, residual risks and remaining submission gates. Report “ready” only when the corresponding gate has real evidence.
