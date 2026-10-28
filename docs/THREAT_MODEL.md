# Threat model

Assets: owner data, session tokens, provider credentials, GitHub write authority,
workspace files and execution budgets. Untrusted inputs: browser requests, model
outputs, fetched evidence, repository text and network responses.

Controls: Argon2 passwords; hashed opaque server-side sessions; SameSite cookies,
CSRF header and Origin checks; encrypted provider tokens; strict input schemas;
owner filters and composite foreign keys; prepared SQL; no legacy shell routes;
fixed provider origins with no redirects; bounded response sizes; exclusive
no-follow note creation; exact expiring approval; transactional continuations;
pre-dispatch intents and read-only uncertain-write reconciliation.

Trust the deployment host, database administrator and encryption-key custodian.
A hostile local administrator can read application memory and files. HTTPS is an
operator requirement for remote access. The service is not a code sandbox and
never accepts arbitrary programs. It does not fetch arbitrary research URLs;
Tavily performs search and excerpts. Approved domains limit evidence selection.

Residual risks: model reasoning can be wrong; citations demonstrate provenance,
not truth. An interrupted external request may remain uncertain if no unique
marker is found in the bounded recent-issue scan. Successful cancellation cannot
roll back an already-dispatched request. Backups retain deleted data until rotated.
See RELEASE_REPORT.md for concrete review findings and regression tests.

## Settings boundary (2026-10-25)

Owner preferences cannot widen operator ceilings, introduce new provider hosts,
access another owner, expose credentials or edit arbitrary environment variables.
Settings/model writes use existing CSRF/session checks and the owner dispatch lock.
A revision conflict requires reload. Provider validation occurs before an atomic
settings/connection-validation commit. New credentials invalidate prior model
validation. Queued configuration cannot override current tighter limits or revoked
connections. Pricing from one model is never applied to another model silently.
Model discovery responses and validation failures are bounded and sanitized.
