# ADR 003 — Typed owner settings with bounded execution snapshots

Accepted 2026-10-25. Keep the existing API/worker/PostgreSQL architecture.
Store owner preferences in PostgreSQL, not in process memory or a browser-managed
.env file. The environment remains the infrastructure and operator policy boundary.
Settings use optimistic revisions; connection secrets remain in their existing
encrypted store and updates are serialized with dispatch/revocation.

New runs record resolved non-secret configuration. Current tighter operator/owner
limits and current connection authority still apply at dispatch. Historical null
snapshots resolve current settings. Skill definition changes invalidate old queued
skill hashes. Model edits validate account visibility and actual inference before
an atomic settings/validation update. Alternate model prices remain unknown.

Unknown token consumption retains its original reservation in usage, rather than
being recalculated using subsequently lowered settings. Legacy unknown records
reserve the maximum supported bound until the rolling daily window expires.

This provides reproducible queued choices without turning old configuration into
an authorization bypass. It adds migrations004/005 and four authenticated routes;
it does not introduce a second scheduler, credential store or agent runtime.
