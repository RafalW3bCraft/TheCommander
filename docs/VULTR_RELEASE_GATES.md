# Vultr release gates — 2026-11-08

Implementation starts from `766479b5b48d9f2957ae3245f3f7a2ddc5072fbf`, on
`vultr` only. Historical evidence is retained; it is not current deployment proof.

| Requirement | Test and environment | Required proof | Missing input / current status |
|---|---|---|---|
| Safe test database | Disposable PostgreSQL 17; guard regressions | Missing/application URLs rejected before setup or teardown | Engineering; FAIL at baseline (unsafe fallback) |
| Preserve owner/data | Original database backup, isolated restore and migration | Original IDs, login, notes and decryptable connections | Source database unavailable; BLOCKED |
| Inference | Text/tool/known-image probes on VM and application | Vultr endpoint, exact model, usage and result | Prior direct probes PASS; app/VM NOT RUN |
| Host containment | Docker/runsc tests on authorized VM | Limits, denied network/canary, cleanup receipts | Docker/gVisor NOT RUN |
| Code workflow | UI → API → worker → actual container | Known output, artifacts, failure/timeout/cancel and model explanation | Engineering; incomplete at baseline |
| Browser workflow | Controlled public HTTPS fixture | Preview/reject/expire/change: zero writes; human approval: exactly one confirmed write | DNS deferred; operator approval required; BLOCKED live gate |
| Private accounts | PostgreSQL owner + two accounts; API and Chromium | Invitations, sessions, roles, object/worker isolation and quotas | Engineering; incomplete at baseline |
| Existing features | Current verification script and both CI workflows | Chat/providers, projects/memory/research/schedules/GitHub/history preserved | Baseline remote CI PASS; candidate NOT RUN |
| HTTPS/judge | Clean external session | TLS, Secure cookies, exact origin and isolated invitation | Operator deferred DNS; BLOCKED |
| Operations | Restore/rollback/restart/concurrency/retention drills | Recorded commands, provenance, measurements and cleanup | Engineering; NOT RUN |
| Submission | Event brief, ruling and signed-in form review | Eligible existing project, real media, working links | Operator/form/DNS; BLOCKED |

Independent console verification of host fingerprint
`SHA256:6GRp23B9wYYyLHCKyb421igSvTO00sHpL/KVIJiDP0M` is pending. Do not
transfer private configuration or original data until it is confirmed. No new
instance, resize, paid extra, Git push or LabLab upload is authorized by this ledger.

For each change record the failing regression, minimal fix, focused rerun,
normal-entry-point check, review and combined candidate result. Distinguish
fixtures, real local services, runc CI and actual hosted gVisor throughout.
