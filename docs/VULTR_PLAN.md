# TheCommander / Vultr implementation plan

Status: implementation authorized; only `vultr` may be changed. Baseline: `96fcd1f8fdd0d64ebba486acb67e2c56e5851b7a` (2026-11-04).

## Analyze → iterate → verify → plan → verify → build

1. Preserve the existing FastAPI/React/PostgreSQL application, keys, defaults, memory service and workflows. Add modules, migration, routes and a Sandbox workspace.
2. Add Vultr as an optional encrypted connection and provider. Sandbox inference always uses Vultr; never silently substitute an existing provider. Models must be configured from the account's live model list; browser verification requires a vision-capable model.
3. Persist project-scoped sandbox jobs, bounded event histories, immutable plans and receipts. Claim jobs atomically; worker interruption fails closed and never replays an approved external write.
4. Execute Python in disposable containers with no network, mounts, inherited credentials, privilege or host execution fallback. Apply time, CPU, memory, PID, filesystem and output limits; destroy each container.
5. Execute a constrained Playwright action language in separate containers. Use per-job internal networks and a public-HTTPS-only egress proxy with operator allowlisted domains, public-IP validation and DNS pinning. Block direct egress, private/metadata addresses, redirects to unapproved domains, downloads, popups and service workers.
6. Observe first, return screenshot and receipt, verify through Vultr vision. Require exact, expiring human approval before every fill/click plan. Bind approval to plan and observed page; fresh-page mismatch aborts before actions. Do not blindly retry external effects.
7. Add React task submission, status timeline, source/plan inspection, screenshot evidence, explicit approve/deny, cancel and receipt export. Preserve all existing navigation and settings.
8. Verify with adversarial policy tests, transport contracts, database/API state transitions and frontend build. Provide opt-in real Docker tests and CI. Never label mocks as live execution evidence.
9. Document deployment, threat model, operator key additions, demo, judging mapping, submission checklist and a Codex continuation prompt. Publish tested commits only to `vultr` using a branch-head lease.

## Scope and release gates

The target is a verifiable agent application, not a claim of matching frontier model intelligence. Existing chat/memory/research capabilities remain intact. Broader product improvements follow reliable execution: artifact workspaces, richer diff review, retrieval evals, streaming, multi-user RBAC and measured reliability/cost.

Required external gates: real Vultr text inference, real Vultr vision inference, Docker containment smoke on the deployment VM, public HTTPS demo, full browser flow with human-approved action against a controlled site, slides and recorded demo, organizer confirmation of existing-project eligibility, final LabLab submission. Do not claim these gates passed without receipts.

No Docker executable/daemon or Vultr credentials were available in the initial editing environment. Existing project eligibility is not explicitly resolved by the retrieved event page/rule book; disclose the baseline and new work and obtain an organizer ruling.
