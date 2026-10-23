# Findings ledger

Independent security review used isolated PostgreSQL schemas and controlled HTTP
transports. No live external issue was created. All fixes require final gates.

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

Review limitation: absence of a reported defect is not a security guarantee.
