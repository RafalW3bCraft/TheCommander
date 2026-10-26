# Findings ledger

Independent security review used isolated PostgreSQL schemas and controlled HTTP
transports. No live external issue was created. All listed fixes passed the final local gates; see RELEASE_REPORT.md.

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
