# Module regression ledger

Audit base: preserved user checkpoint `c69b86b`, plus the working-tree audit fixes.
Earlier release gate: `docs/evidence/final-verification.txt` (42 tests); current
gate: `docs/evidence/audit-verification.txt`. A clean Git status alone is not
evidence that a module has been verified.

Dependency evidence: `uv run python -m scripts.audit_repository` produces Python
import/route edges in `docs/evidence/recursive-inventory.json`. Frontend consumers
are traced in `CLICK_PATH_AUDIT.md`; generated types come from
`scripts/export_openapi.py` and `frontend/package.json`. The image and process
edges are explicit in Dockerfile and compose.yaml. Dynamic vendor behavior is
unverified unless the corresponding live artifact names the provider and scope.

Set `TEST_DATABASE_URL` to the isolated PostgreSQL service and use Node 22.
Commands below operate on test schemas/local files. Explicit live scripts incur
provider usage; they do not authorize external issue writes.

| Module | Downstream consumers | Acceptance command |
|---|---|---|
| Settings, database, migrations, auth, memory | All API/domain services, worker, frontend | `uv run pytest tests/test_auth_memory.py tests/test_workflows.py` |
| Providers, inference, connections, broker, engine | Runs, worker, approvals, frontend activity | `uv run pytest tests/test_workflows.py` |
| Runs, schedules, worker, workspace | Today, Skills, Activity, Notes | `uv run pytest tests/test_workflows.py` plus browser command below |
| Contracts and routes | Generated OpenAPI, TypeScript client, all pages | `uv run python -m scripts.export_openapi` then `npm --prefix frontend run api:types` and `npm --prefix frontend run build` |
| Frontend state and forms | All user workflows | `npm --prefix frontend run lint` and `npm --prefix frontend run test:e2e` |
| Packaging and startup | API, independent worker, PostgreSQL and durable volumes | `uv run python -m scripts.clean_release_smoke` |
| Migrations and persistent data | Backup/restore and retained-volume upgrade | `uv run python -m scripts.backup_smoke`; releasecheck Compose drill in RELEASE_REPORT.md |
| Actual inference/search connectors | Live model responses and source evidence | `uv run python -m scripts.evaluate_live`; `uv run python -m scripts.live_research_smoke` |
| Legacy archive and ECC catalog | Development/reference only; no runtime imports | `uv run python -m scripts.audit_repository`; archive hash and image allowlist review |

Propagation rule: any externally observable change runs the changed module and
all listed downstream gates. Schema or API changes regenerate types and rerun the
browser. Provider/context changes rerun the bounded affected live check when
credentials are present. Documentation-only changes need link/diff/secret checks,
not repeated paid inference. All offline gates are collected by `scripts/verify.sh`.

Outcome references are recorded in RELEASE_REPORT.md. The initial browser attempt
failed a suite timeout and a test navigation error; these are retained in
`audit-browser-initial-failures.txt`. They are not a green result. Unknown GitHub
live behavior remains an explicit open edge even when local gates pass.

## Settings and assistant release increment

- Persistent typed settings: reload/restart, revision conflict, scope isolation,
  model discovery/validation, secret replacement, schedule snapshots and lower limits.
- Unknown usage cannot be discounted by lowering a later context/output setting.
- Simultaneous connection edits have one winner; stale revoked forms cannot
  restore encrypted credentials. Expired explicit memory permits active inference.
- Delayed conversation A history cannot overwrite B or a cleared conversation;
  old-handler reproduction fails immediately before polling can conceal it.
- Unique cancellation status selector preserves the original stale-poll assertion.
- Clean schema001–003 upgrade preserves memory and executes a legacy null snapshot.
- Container recreation retains settings, memory and notes in isolated volumes.

Evidence: release-verification.txt, release-upgrade-settings.txt,
conversation-race-red.txt, usage-reservation-red.txt, usage-reservation-green.txt,
release-clean-build.txt and backup-restore.json. Earlier iteration logs may include
failed harness setup or incomplete gates; use the dated final release report as
an index, not filenames containing 'green' as proof of success.
