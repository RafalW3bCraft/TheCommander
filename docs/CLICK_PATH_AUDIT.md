# Click-path audit — 2026-10-24

Scope: all five release destinations plus authentication, shared request state and
run-detail dialogs in `frontend/src/main.tsx` and `frontend/src/api.ts`. The initial
state map was followed by a bounded independent reviewer, which reported the five
findings below. The primary agent implemented fixes and authored this report;
the reviewer's documentation follow-up hit a host usage limit. No independent
browser sign-off is claimed.

## State map

| State owner | Changes | Resets and interactions |
|---|---|---|
| App | Owner, current page, boot/error | Sign-out or authenticated 401 clears owner and CSRF, unmounting private page state |
| useJob | Pending request count, latest error | Each request increments/decrements independently; completion of one cannot enable controls while another is active |
| MemoryPage | Items, search, editing, loading, request version | Successful save resets only the current editor; mutation refresh reads current query; deleting the edited item clears the editor |
| Today | Conversation selection, messages, runs, schedules, usage, worker | New conversation clears selection; delete and queue are checked server-side; selecting a run mounts keyed details |
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
and timings are in [browser-results.json](evidence/browser-results.json); the final
gate log is [audit-verification.txt](evidence/audit-verification.txt).

## Touchpoint-to-route trace

API paths below are relative to `/api`. Static links and disclosure controls change
views only; mutations go through the authenticated CSRF-aware API client.

| Touchpoints | Sequence and persisted boundary |
|---|---|
| Bootstrap / Sign in / Sign out | `/auth/status` → POST `/auth/bootstrap` or `/auth/login` → owner+CSRF; POST `/auth/logout` → clear session/UI |
| Navigation / brand / Close details | Change destination or selection; no hidden backend write |
| Memory search / Export | GET `/memory?q=` → guarded list; GET `/memory/export` → local JSON download |
| Save memory / Edit / Save correction / Cancel edit / Delete | Local selection → POST or revision-bound PUT `/memory` → refresh; cancel only clears selection; DELETE removes owned row and clears matching editor |
| Today task composer / conversation selection / new / delete | POST `/runs` returns run and conversation; GET conversation/messages; DELETE conversation rejects unresolved active work |
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

## 2026-10-25 increment

Assistant replaces the Today label; Settings replaces the Connections destination.
Settings → Connections retains the existing scoped credential forms and notes.
Settings → Model and limits discovers models, validates/saves typed settings and
reloads conflicts. Data and privacy links to memory controls; System refreshes
redacted API/database/worker health. A revision accompanies connection updates.
Conversation history now ignores responses from superseded selections. Six browser
scenarios cover the existing workflows plus delayed history and settings persistence.
The settings screenshot and desktop/tablet/mobile screenshots were opened directly;
controls are legible and primary actions remain within the viewport. Screenshots
contain explicitly controlled vendor outputs, not live provider receipts. No
approved visual baseline or full screen-reader certification is claimed.
