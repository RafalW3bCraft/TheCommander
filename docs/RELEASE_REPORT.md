# Release report — 2026-10-28 UTC

## Current candidate

**Implemented:** approved legacy retirement, documentation consolidation, strict
Compose-smoke isolation, fail-closed required packaging inputs, and correct parsing
of Unicode-delimited evidence citations. The complete
ECC catalog, private configuration, database volumes and Git history are retained.
The two root prompt deletions predate this pass and remain preserved.

Starting HEAD: `1294bfa8733a5ae7057cf2152f057a418db3c67b`. The owner subsequently
committed implementation as `f8c0b1a` and `d04b33a`. Current source baseline:
`d04b33a862ff3e119e6e1fb2c32fb4f4a83fd4c6`, plus release-documentation and evidence
updates. Final tested source and archive SHA256 are in
[evidence/release-manifest.json](evidence/release-manifest.json). The cleanup
manifest records each removed path, hash, reason and local preservation archive:
[evidence/cleanup-removals.json](evidence/cleanup-removals.json).

## Current verification

**Locally verified:** the October 28 full gate after the citation fix passed
87 Python tests with 91.14% first-party application coverage and seven Chromium
scenarios. Ruff, formatting, mypy, generated OpenAPI/TypeScript, frontend formatting,
lint/build, Python/npm dependency audits and configured-secret scan passed.
See `cleanup-final-verification.txt` and its process record. The fresh run against
the current committed candidate also passed, exit 0 at 11:59:31 UTC in 244.211 s
(`cleanup-candidate-verification.txt` and its process JSON). Test database setup uses the
actual `scripts/test_db.sh` URL, `postgresql://watcher@127.0.0.1:55432/postgres`;
Node is 22.23.3. Controlled provider transports are separate from live evidence.

**Locally verified:** clean-source Compose startup and retained-volume recreation,
plus isolated database/notes backup restoration, passed again at 11:55/11:54 UTC.
See `cleanup-final-clean-build-process.json` and `cleanup-final-backup-process.json`.
The final package integrity/build result is recorded in
`packaged-release-verification.json`; reproducibility is in
`package-reproducibility.json`. Match those fingerprints to `release-manifest.json`
before using a package. Generated evidence is deliberately outside package inputs.

**Live verified:** the post-fix Nebius evaluation passed 30/30 bounded fictional
cases: 29 model calls, 28,061 reported tokens, no missing usage metadata, median
task latency 4,429 ms and maximum 7,325 ms. Model:
`nvidia/nemotron-3-super-120b-a12b`, Token Factory endpoint, temperature 0.2,
2048 output-token ceiling. Cost is unknown. See `live-evaluation.json` and
`cleanup-final-live-evaluation-process.json`; this is not a general quality benchmark.
Tavily validation and search persisted five sources in 3,106 ms; version/language
relevance still needs human review (`live-research-smoke.json`).

**Live verified:** GitHub repository read, cited engineering briefing and saved
note, research proposal, exact UI edit/approval, and one confirmed issue in the
explicitly authorized private `AetherSilva/thecommander-acceptance` repository.
The separate authenticated GET on October 28 matched the exact approved title,
body and correlation marker: [issue #1](https://github.com/AetherSilva/thecommander-acceptance/issues/1).
Evidence: `cleanup-github-confirmation.json`, `cleanup-github-executed.json`, and
`cleanup-live-engineering-briefing-final.json`. Approval was clicked once.
The browser opened the receipt URL, but GitHub returned its private-repository
not-found page without an authorized website login; visual inspection of the
GitHub issue contents is **Blocked** on that login. API content verification passed.

**Live verified:** follow-through was scheduled in the real UI, the browser closed
before dispatch, and the separate worker used Nebius and saved notes. After
restarting the isolated API and worker, settings/revision, memory, conversations,
schedule, note contents and GitHub receipt matched. Browser reopening displayed
the result, receipt and saved briefing. See `cleanup-live-follow-through.json`,
`cleanup-live-persistence.json` and `cleanup-live-browser-notes-process.json`.
These checks use an isolated owner/schema on port 8022, not the owner's main account.

Desktop, tablet, mobile, Settings and disconnected-state screenshots were directly
inspected. Automated axe checks belong to the browser suite; manual layout review
is separate and is not approved-baseline visual regression testing. Commands,
source hashes, dates, outcomes and limitations are indexed in `evidence-index.json`.

## Current blockers and readiness

GitHub credentials, repository selection and the one-issue write gate are resolved
for the isolated acceptance owner. No additional issue, remote deployment or source
publication is authorized by that test. Configure the intended owner separately;
acceptance credentials and state are not judge-access credentials.

Archive comparison: **Blocked** until the actual supplied archive path is provided.
Remote HTTPS, dedicated judge access, monitoring, backups/quota and availability:
**Blocked** until host/domain/access and specific deployment authority exist.
Entrant eligibility and publication/video/submission authorization remain required.
The generated release archive is not the supplied archive.

Locally ready: application and live acceptance **Locally verified / Live verified**;
use the matching final package-verification record for artifact readiness.
Deployment verified: disposable local Compose **Locally verified**; remote **Not run**.
Submission ready: **Blocked** by public artifact/source, judge access, eligibility,
video and delivery gates. No organizer acceptance is claimed.

## Review findings for this increment

- F18 (medium): standalone compose_smoke defaulted to the owner application port.
  Three controlled regressions reached forbidden effects before the fix. The helper
  now requires the isolated runner’s explicit URL, project, scratch root and marker
  before writing or creating an HTTP client. Marker mismatches and links fail closed.
- F19 (medium): packaging silently skipped missing required files. A controlled
  regression produced a partial archive before repair. Required release inputs now
  fail before output creation; obsolete prompt paths are removed from the allowlist.
- F20 (medium, repaired): real briefing output wrapped valid evidence URLs in `】`,
  which the citation parser incorrectly included in the URL and rejected. The
  controlled regression failed before repair and passed afterward; invalid paths
  and an unauthorized second URL remain rejected. See citation-delimiter-red.txt,
  citation-delimiter-green.txt and tests/test_workflows.py. No citation allowlist
  bypass or silent provider fallback was added.
- Live research limitation: the first verbose research request returned no evidence
  and failed visibly. A shorter query yielded a proposal, which was edited to remove
  unsupported guarantees and label historical sources before approval. Retained
  failures are cleanup-live-research-to-action-final.json and the earlier briefing
  failure/diagnostic reports. Transport success does not establish factual quality.
- Unresolved: the October 27 malformed Nebius continuation has no retained raw
  response/root-cause evidence. Later successes do not erase it.
- Limitation: approved search domains do not ensure source freshness or relevance.
- Publication: GitHub About still describes Flask/OpenAI/Anthropic; prepared wording
  is in HACKATHON_CHANGES.md and requires authorized publication.

## Release acceptance checklist

The final candidate must pass static/backend/browser/audit/secret gates, isolated
clean startup and retained-volume recreation, backup restoration, package integrity
and reproducibility. Every integration shown in the demonstration must have live
evidence. No unresolved critical/high defect in reviewed scope may be concealed.
GitHub acceptance requires read → cited briefing → exact proposal → one approval →
issue creation → independent GET → receipt opened → persistence after restart.
Uncertain writes require reconciliation, never blind retries.

A public matching source revision, tested HTTPS judge deployment, English materials,
public YouTube video under three minutes, significant-update narrative and observed
technology feedback are separate submission gates. No hosted URL, video, submission
or organizer acceptance is claimed. See JUDGE_GUIDE.md and DEMO_SCRIPT.md.

## Historical repaired findings

The historical independent security review used isolated PostgreSQL schemas and
controlled HTTP transports; it created no live issue. This continuation used
self-review, not a new independent reviewer. Current live evidence is above.

| ID | Severity | Reproducer | Fix | Regression |
|---|---|---|---|---|
| F01 | High | POST succeeds, confirmation GET returns `[]`; action stuck executing | Validate shapes, classify all post-dispatch failures uncertain, preserve uncertain state in worker | test_malformed_write_confirmation_stays_reconcilable |
| F02 | Medium | Validation dispatches inference with unknown cost under configured cap | Shared pre-dispatch budget reservation and usage accounting for validation and runs | test_validation_enforces_budget_and_accounts_usage |
| F03 | Medium | Confirmation body differs but retains marker | Compare full approved body plus marker exactly | test_malformed_write_confirmation_stays_reconcilable |
| F04 | Medium | Chunked 100 KB login bypasses Content-Length guard | Count actual streamed bytes before parsing | test_chunked_oversized_request_rejected |
| F05 | Medium | Crash between action approval and run queueing | One transaction for action/run/event transitions on approve/edit | test_approval_transaction_rolls_back_on_queue_failure |
| F06 | Medium | Unknown/Fake timezone raises server exception | Translate ZoneInfo failure into validation error | test_invalid_timezone_is_validation_error |
| F07 | High | pip-audit reports cryptography 47 vulnerabilities | Upgrade dependency and regenerate uv.lock | python-audit.txt final result |
| F08 | Medium | Compose context includes frontend dependencies | Explicit dockerignore exclusions; one build target | compose-build.txt |

| F09 | Medium | Host Podman splits inline Python health-check command; healthy API marked unhealthy | Use `python -m commander.healthcheck` | Rebuilt container reports healthy; HTTP readiness succeeds |
| F10 | Medium | Action body marker omitted from preview/hash | Include marker in exact arguments and preview; invalidate legacy approvals in migration 002 | test_exact_preview_binds_the_visible_correlation_marker |
| F11 | Medium | Crash after confirmed issue leaves run result absent and recovery error | Restore durable receipt result and clear error without repeating dispatch | test_crash_after_confirmed_issue_restores_receipt_result |
| F12 | Low | Credential expiry accepted by API but no UI field | Add optional local-time expiry control and distinct expired status | test_connection_expiry_is_distinct_and_blocks_dispatch; browser forms |
| F13 | Low | Host default Node 20 below installed axe dependency requirement | Declare Node 22 engine; use installed 22.23.3 for final gates | final-verification.txt; Node 22 container build |

F01–F06 came from the independent security review. F07–F13 came from primary
implementation/review/operational checks. No unresolved critical/high finding is
known from these reviews. This is not an exhaustive security certification.

Review limitation: absence of a reported defect is not a security guarantee.

## F14 — Configuration changes could undercount unknown usage (2026-10-25)

Reproducer: dispatch with a 32000-character context / 2048-token output allowance;
lose the provider response; lower context to4000 and output to512. The previous
budget check recomputed the unknown request at the new smaller reservation,
allowing another request under a 20000-token daily cap. The new regression failed
with DID NOT RAISE. Migration005 persists each original reservation; legacy unknown
rows use the maximum supported bound. Retest: usage-reservation-green.txt.

## F15 — live probe returned success on failed checks (medium; repaired)

The standalone Nebius smoke command always exited zero, even for missing keys,
unavailable models, provider errors or invalid tool responses. This could mislead
automation using its process status. Reproduced with six controlled scenarios in
tests/test_live_probe.py; red evidence is live-probe-red.txt. It now requires all
three acceptance checks, records passed/status, and exits 0 only on success, 2
for absent credentials and 1 for other failures. The same tests pass in
live-probe-green.txt. The corrected probe was also run against actual Nebius;
controlled regression results are separate from that live evidence.

## F16 — release archive bytes varied for identical source (low; repaired)

The packager used gzip's current timestamp, so identical source fingerprints could
produce different archive digests at the same artifact path. A deterministic clock
regression reproduced this: package-reproducibility-red.txt. Tar and gzip metadata
are now fixed. Repeated builds are byte-identical in the tested runtime. The public
verify_package script replaces reliance on a private session helper and verifies
exact current source before extracting/executing the generated test build.
Controlled regressions reject stale content, digest tampering, unsafe entries,
symlinks, duplicates, missing and extra files; package-reproducibility-green.txt.
No generic safety certification for arbitrary supplied archives is claimed.

## F17 — live acceptance failures did not fail the command (medium, repaired)

The 30-task evaluator wrote per-case failures but returned exit code zero. A
controlled full-run regression reproduced this (`DID NOT RAISE SystemExit` in
`oct27-evaluation-exit-red.txt`). The evaluator now writes an explicit evidence
status and exits 1 unless every expected scenario passes. Cleanup still executes.
Two controlled regressions exercise success and failure; no live transport or
application policy was changed. See `test_live_evaluation_exit.py` and
`oct27-evaluation-exit-green.txt`. This repairs release automation, not model quality.

## October 27 live observation — intermittent invalid completion (unresolved cause)

The first real Nebius smoke passed discovery and tool proposal, then failed with
`malformed_response` on continuation. The failure remains in
`oct27-live-smoke-first.json`; the command exited 1. One bounded diagnostic rerun
passed unchanged (606 reported tokens), and a separate 30-task application
acceptance run passed 30/30. No raw response from the first failure was retained,
so its precise response shape/root cause is unconfirmed. The failed continuation's
usage is unknown. Do not describe these observations as a repaired provider fault
or uninterrupted live reliability. Application validation was not weakened.

## Historical evaluation — 2026-10-27

The following is the recorded October 27 result, not the latest evaluation.
Current [live-evaluation.json](evidence/live-evaluation.json) is the October 28
rerun described above, generated by `uv run python -m scripts.evaluate_live`.
Endpoint: https://api.tokenfactory.nebius.com/v1.
Model: `nvidia/nemotron-3-super-120b-a12b`; temperature 0.2; maximum output 2048 tokens.
Fictional tasks used isolated PostgreSQL state and a separate worker process.

| Scenario category | Cases | Passed |
|---|---:|---:|
| New-conversation recall of a saved codename | 10 | 10 |
| Bounded planning response | 4 | 4 |
| Follow-through with persistent local note | 4 | 4 |
| Actual model-proposed workspace tool calls | 3 | 3 |
| Unsafe shell requests produce no unauthorized action | 3 | 3 |
| Correction and deletion affect subsequent recall | 2 | 2 |
| Cancel before execution | 2 | 2 |
| Disconnected skill fails visibly | 2 | 2 |
| Total | 30 | 30 |

26 cases reached inference, producing 29 actual model calls and 27,974 reported
tokens. The remaining four check cancellation/disconnection before inference.
No usage call lacked usage metadata. Currency cost is unknown, not zero.
Across all 30 cases, median task latency was 5,089.5 ms; maximum was 7,705 ms.
These timings include API/polling/worker overhead and are not model-only latency.

The separate [live smoke](evidence/live-smoke.json) checked account model listing,
a real tool proposal and tool-result continuation. It is additional evidence,
not part of the 30-case count.

Limits: this is a small repeated acceptance set, not 30 independent quality
benchmarks or a statistical reliability claim. Planning checks are bounded output
acceptance, not expert grading. The application broker prevents shell execution;
three model responses do not prove resistance to every prompt injection.
At that historical checkpoint, no live GitHub task was possible with its credential
and repository scope; the October 28 authorized acceptance resolves that gap.
Tavily was not included in these 30 scenarios; a subsequent separate live smoke
validated its connection and persisted four approved-domain search results. Recovery,
write uncertainty, concurrent claims and provider failures use deterministic
PostgreSQL/controlled-transport integration tests in `tests/test_workflows.py`.
Those tests are separate from the live evaluation sample. No live issue creation,
provider outage, write timeout, or remote production uptime was measured.

Unit/integration coverage measures first-party `commander` Python code, including
worker/recovery/domain/API logic. The CLI utility is excluded; scripts, generated
contracts, frontend and legacy modules are outside this Python coverage metric.
Browser scenarios and operational drills separately exercise the frontend,
separate worker, clean container startup and database/notes restore.

Additional Tavily evidence: [live-research-smoke.json](evidence/live-research-smoke.json),
2026-10-27 15:32 UTC. Validation plus one broker search used `docs.python.org`.
The search took 5,622 ms and persisted four timestamped results. It checks the
connector and evidence path, not a completed GitHub-dependent skill. Results span
versions/languages, so source selection remains a quality consideration; domain
restrictions alone do not guarantee the most relevant result.

The complete deterministic gate is recorded in oct27-verification.txt; its
application coverage excludes scripts and frontend code. Two new controlled
regressions ensure the 30-task command succeeds only when every scenario passes
and persists failures before returning a nonzero exit code. The live evaluation
above completed immediately before that CLI-only exit repair; application inference,
context, tools and the case definitions are unchanged.

The first October 27 standalone smoke failed on continuation with an invalid
completion after a valid tool proposal. Its response body was not retained, so
root cause and failed-call usage are unknown. See oct27-live-smoke-first.json.
One unchanged diagnostic rerun passed at 15:33 UTC (two calls, 606 tokens), with
sanitized response shapes in oct27-live-response-shapes.json. The independent
30-task evaluation was then run because the initial failure warranted broader
acceptance. This does not erase the failed probe or establish continuous reliability.
