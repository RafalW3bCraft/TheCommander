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

Current outcomes are indexed in RELEASE_REPORT.md; implementation is not live verification.

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
| PACKAGE-01 | package_release → fixed archive metadata → verify_package integrity → clean Compose/persistence | test_release_package.py; package-reproducibility-red/green.txt; packaged-release-verification.json |

Latest results: RELEASE_REPORT.md and cleanup-candidate-verification.txt.

## October 27 verification coverage

| Requirement | Path | Evidence |
|---|---|---|
| VERIFY-02 | evaluate_live → per-case acceptance → evidence and process exit | test_live_evaluation_exit.py; oct27-evaluation-exit-red/green.txt |
| UI-02 | Memory empty search; Settings revoke → run failure → reload | seventh Playwright scenario; browser-disconnected.png |

## UI state and click-path acceptance

## State map

| State owner | Changes | Resets and interactions |
|---|---|---|
| App | Owner, current page, boot/error | Sign-out or authenticated 401 clears owner and CSRF, unmounting private page state |
| useJob | Pending request count, latest error | Each request increments/decrements independently; completion of one cannot enable controls while another is active |
| MemoryPage | Items, search, editing, loading, request version | Successful save resets only the current editor; mutation refresh reads current query; deleting the edited item clears the editor |
| Assistant | Conversation selection, messages, runs, schedules, usage, worker | New conversation clears selection; delete and queue are checked server-side; selecting a run mounts keyed details |
| SkillsPage | Definitions, task forms, selected run | Enqueue selects returned durable run; closing details clears selection |
| ConnectionsPage | Connection records and revision-bound forms | Saved/imported records refresh list; revision keys reset forms to persisted configuration |
| Activity/RunDetail | List, selected run, detail snapshot | Key changes reset detail; request sequence prevents older poll responses replacing newer mutations |
| ActionCard | Proposal editor and exact arguments | Edit invalidates previous approval; approve submits server-issued hash, then refreshes detail |
| Notes | List, selected filename, content, request version | Selection clears old content; only latest selected note response can publish content |

## Findings and corrected sequences

| ID / severity | Trigger and previous result | Fix and expected final state |
|---|---|---|
| CP01 / medium | Save A begins under search A; search changes to B; save completion refreshes captured A and overwrites B results | Stable refresh reads a current-query ref; sequence counter rejects older results. B remains selected and displayed |
| CP02 / medium | Save A is pending; edit B or cancel remains available; completion of A resets the new draft | Disable editor-switch/cancel/delete while any operation is pending; useJob counts overlapping operations |
| CP03 / medium | Delete the memory currently being corrected; stale correction form remains and later saves against a missing record | Delete clears editing when IDs match; form returns to “Remember something” |
| CP04 / medium | Old run poll arrives after cancel/approve and restores pending proposal UI | Only the latest detail request can publish its result. Backend hash/status checks remain authoritative |
| CP05 / medium | Open slow note A, then fast B; A arrives last and overwrites B | Note request sequence guards content and selected filename is displayed |

The delayed-response browser regression deliberately holds real local API responses
and releases them out of order. It does not invent provider success. Test results
and timings are in [browser-results.json](evidence/browser-results.json); current results are in RELEASE_REPORT.md.

## Touchpoint-to-route trace

API paths below are relative to `/api`. Static links and disclosure controls change
views only; mutations go through the authenticated CSRF-aware API client.

| Touchpoints | Sequence and persisted boundary |
|---|---|
| Bootstrap / Sign in / Sign out | `/auth/status` → POST `/auth/bootstrap` or `/auth/login` → owner+CSRF; POST `/auth/logout` → clear session/UI |
| Navigation / brand / Close details | Change destination or selection; no hidden backend write |
| Memory search / Export | GET `/memory?q=` → guarded list; GET `/memory/export` → local JSON download |
| Save memory / Edit / Save correction / Cancel edit / Delete | Local selection → POST or revision-bound PUT `/memory` → refresh; cancel only clears selection; DELETE removes owned row and clears matching editor |
| Assistant task composer / conversation selection / new / delete | POST `/runs` returns run and conversation; GET conversation/messages; DELETE conversation rejects unresolved active work |
| Schedule / edit / pause / resume / delete | POST/PUT/DELETE `/schedules`; timezone-qualified instant, revision and enabled flag persisted; worker dispatches independently of browser |
| Usage and worker status | GET `/budgets` and `/worker`; unknown money cost remains unknown |
| Three skill task forms | GET `/skills` → POST `/runs` with selected ID → keyed detail; engine enforces tool allowlist and version |
| Connection save / test / revoke / import | PUT `/connections/{kind}` → refresh; POST validate records actual validation state; DELETE revokes; import preserves existing/revoked configuration |
| Load saved notes / select / create | GET `/notes`; guarded GET `/notes/{name}`; POST `/notes` writes exclusive owner-scoped file and refreshes list |
| Activity refresh / select | GET `/runs` → keyed GET `/runs/{id}` with events, evidence and actions |
| Cancel further work / Check saved notes | POST run cancel → guarded refresh; POST reconcile-notes verifies existing content hashes without another write |
| Edit proposal / save new approval / cancel editor | PUT `/actions/{id}` with exact proposal → new hash/revision; local cancellation discards draft |
| Approve exact issue / Check external receipt | POST approve with hash queues worker; POST reconcile does read-only marker/argument verification; refresh exposes result |
| Evidence / verified receipt links | Display persisted, validated source/receipt URL; external new tab has noreferrer; link opening does not create an issue |

Source review also checked revision remounts, preserved connection scopes,
cross-page run selection, expired sessions, errors, empty collections and disabled
controls. Browser coverage is representative and includes the identified races;
it is not exhaustive testing of every possible interleaving or screen reader.


## Downstream verification

| Module | Downstream consumers | Acceptance command |
|---|---|---|
| Settings, database, migrations, auth, memory | All API/domain services, worker, frontend | `uv run pytest tests/test_auth_memory.py tests/test_workflows.py` |
| Providers, inference, connections, broker, engine | Runs, worker, approvals, frontend activity | `uv run pytest tests/test_workflows.py` |
| Runs, schedules, worker, workspace | Assistant, Skills, Activity, Notes | `uv run pytest tests/test_workflows.py` plus browser command below |
| Contracts and routes | Generated OpenAPI, TypeScript client, all pages | `uv run python -m scripts.export_openapi` then `npm --prefix frontend run api:types` and `npm --prefix frontend run build` |
| Frontend state and forms | All user workflows | `npm --prefix frontend run lint` and `npm --prefix frontend run test:e2e` |
| Packaging and startup | API, independent worker, PostgreSQL and durable volumes | `uv run python -m scripts.clean_release_smoke` |
| Migrations and persistent data | Backup/restore and retained-volume upgrade | `uv run python -m scripts.backup_smoke`; releasecheck Compose drill in RELEASE_REPORT.md |
| Actual inference/search connectors | Live model responses and source evidence | `uv run python -m scripts.evaluate_live`; `uv run python -m scripts.live_research_smoke` |
| Preserved ECC catalog | Development/reference only; no runtime imports | `uv run python -m scripts.audit_repository`; full artifact hashes |

Propagation rule: any externally observable change runs the changed module and
all listed downstream gates. Schema or API changes regenerate types and rerun the
browser. Provider/context changes rerun the bounded affected live check when
credentials are present. Documentation-only changes need link/diff/secret checks,
not repeated paid inference. All offline gates are collected by `scripts/verify.sh`.


## Cleanup acceptance

| ID | Guarantee | Regression |
|---|---|---|
| VERIFY-03 | Unisolated Compose smoke exits before writes or HTTP; marker binds target | test_smoke_isolation.py |
| PACKAGE-02 | Missing required inputs cannot create a partial release | test_release_package.py |
| INF-02 | Unicode citation delimiters preserve exact source validation | test_workflows.py; citation-delimiter-red/green.txt |

## October 28 live workflow evidence

| Requirement | Status | Evidence and limit |
|---|---|---|
| SKILL-01 / FILE-01 | Live verified | cleanup-live-engineering-briefing-final.json; saved note reopened through Settings; factual recommendations still require review |
| SKILL-02 / ACT-01 | Live verified | cleanup-github-executed.json and cleanup-github-confirmation.json; exact UI edit/one approval, independent GET; private website contents require GitHub login |
| SKILL-03 / JOB-01 | Live verified | cleanup-live-follow-through.json; real browser scheduled then closed before dispatch |
| SETTINGS-01 / MEM-01 / CHAT-01 / REC-01 | Locally verified | cleanup-live-persistence.json; settings, memory, conversations, schedules, note hashes and receipt retained across isolated API/worker restart |

No intentional live write failure was injected. Uncertain-write recovery remains
a controlled-transport verification, distinct from the confirmed live issue.
