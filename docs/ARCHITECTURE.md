# Architecture

React/TypeScript/Vite serves five views. FastAPI serves the built frontend and
same-origin JSON API. PostgreSQL owns all authoritative records. A separate
Python worker polls durable schedules and claims queued runs. No browser timer
executes tasks. No Redis or second scheduler is required.

Feature modules under `commander/` separate authentication, memory, connections,
provider HTTP, action policy, inference budgets, runs and scheduling. SQL is
parameterized through psycopg. Pydantic rejects extra input fields. OpenAPI
response contracts generate frontend types in `frontend/src/api-schema.d.ts`.

A model can propose a typed operation. The broker checks skill scope, owner,
connection revision and active lease before dispatch. It cannot grant itself
permissions. Only the configured repository and approved search domains are
available. Network destinations are hard-coded provider HTTPS hosts; redirects
are disabled. Search-result pages are not fetched by this server.

Approval commits the action and queued continuation together. External writes
persist intent before dispatch. GitHub has no assumed idempotency key: a unique
marker supports bounded read-only reconciliation after an uncertain response.
There is no general exactly-once promise. Cancellation stops future dispatch and
cannot undo a request already sent. Revoke/cancel and dispatch serialize using
an owner advisory lock. One active run per owner bounds model concurrency.

Schedules record UTC instants and IANA display zones. Recurrence means elapsed
seconds, not fixed local wall time; daylight-saving changes can shift displayed
hours. Missed intervals coalesce into one run. Unique schedule/occurrence keys
and transactional locks prevent duplicate occurrence creation. Three read-only
attempts are the crash-recovery limit. Writes and note intents are not blindly
repeated.

The `commander` schema is independent of the existing `public` draft schema.
See ADR 001. Session and provider secrets never enter frontend storage or model
parameters. Local storage is owner controlled; selected context leaves the host.
