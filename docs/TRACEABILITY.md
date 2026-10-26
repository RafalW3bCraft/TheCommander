# Requirement traceability

Statuses below describe implementation; definitive test/live results are in
RELEASE_REPORT.md and evidence files. Controlled transports do not certify providers.

| ID | UI → API | Domain/data | Tests / evidence |
|---|---|---|---|
| AUTH-01 | Login → /auth/bootstrap,login,logout | auth.py; owners/auth_sessions | test_auth_memory_lifecycle; cross-owner and CSRF tests; browser login |
| MEM-01 | Memory forms/search/export → /memory | memory.py; memories | lifecycle, inferred conflict, cross-owner, restart recall |
| CHAT-01 | Assistant composer/history → /runs,/conversations | engine.py; messages/conversations | test_recall_after_new_app_and_new_conversation |
| INF-01 | Run/test connection → broker/provider | inference.py/providers.py; usage/events | outage/malformed/citation/budget tests; live-smoke.json and live-evaluation.json |
| CON-01 | Settings connections save/test/revoke → /connections | connections.py; encrypted connections | masking/validation/expiry/revocation and browser forms; live-research-smoke.json |
| ACT-01 | Activity preview/edit/approve/reconcile → /actions | broker.py; actions/events | edit/hash/replay/expiry/revoke/uncertain-write tests |
| SKILL-01 | Skills briefing → /runs | engine+broker; evidence/notes | test_engineering_briefing_cites_and_saves |
| SKILL-02 | Skills research → /runs | engine+broker; actions/evidence | research approval and malformed confirmation tests |
| SKILL-03 | Skills follow-through → /runs | engine+workspace; notes/events | scheduled follow-through and browser skill tests |
| JOB-01 | Assistant schedule create/edit/pause/delete → /schedules | schedules.py/worker.py; schedules/runs | concurrent occurrence and edit/pause/delete tests |
| REC-01 | Activity cancellation/uncertainty → /runs,/actions | lease/intent/recovery | crash, lost response, concurrent claim, cancellation tests |
| FILE-01 | Settings connections/files → /notes | workspace.py; no-follow exclusive files | traversal/symlink/create/read checks |
| UI-01 | Five destinations | frontend/src | tsc/build/lint; Playwright desktop/mobile/keyboard/axe |
| OPS-01 | Readiness + worker status | Compose/migrations/CLI | backend migrations; Compose and backup/restore smoke |

Every advertised button performs a persisted operation, fetch, or explicit view
transition. Unknown vendor status stays unconfigured/configured/stale/failed;
validation of GitHub reads does not imply live issue-write permission.

Historical baseline (2026-10-23): all IDs above implemented and covered by the local gates.
42 PostgreSQL integration/contract cases and two Chromium scenario suites passed.
Nebius, Tavily and workspace have live evidence. ACT-01 and the complete live
SKILL-01/SKILL-02 workflows await a real GitHub token, selected disposable repository
and explicit write-test authority. Exact evidence and remaining checks are in
RELEASE_REPORT.md; live scope must not be inferred from the implementation column.

## Owner settings release increment (2026-10-25)

| Requirement | UI → API → persistence/execution | Verification |
|---|---|---|
| SETTINGS-01 | SettingsPage → GET/PATCH settings → owner_settings revision → shared resolver | test_release_settings.py: revision, bounds, restart, isolation |
| SETTINGS-02 | Model discovery/selection → models/settings → Nebius account validation | controlled model discovery/failure/replacement tests; live default-model evaluation |
| SETTINGS-03 | System section → authenticated system/status → database/worker/configured booleans | API redaction and browser settings scenario |
| CON-02 | Connection form revision → save under owner lock → revoke-safe merge | stale revocation and simultaneous edit regressions |
| CHAT-02 | Conversation selection → history request → guarded response | delayed-history browser regression; red/green evidence |
| MEM-02 | Recall → eligible explicit/inferred records → inference | expired-explicit and bounded-context regressions |
| SKILL-SCHEMA-01 | Schema definitions → validated input/output → enforced ceilings | skill ceiling regression; persisted skill_output event |
| JOB-02 | Enqueue/schedule dispatch → settings_snapshot → effective execution | schedule and tighter-current-limit regressions |
| OPS-02 | Compose HTTPS overlay → reverse proxy → Secure production sessions | config validation; remote HTTPS remains Blocked |

| VERIFY-01 | CLI live smoke → provider checks → persisted evidence and process exit | test_live_probe.py; live-probe-red/green.txt; live-smoke.json |

Latest results: CONTINUATION_REPORT.md and continuation-verification.txt.
