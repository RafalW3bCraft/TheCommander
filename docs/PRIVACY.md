# Privacy and deletion

PostgreSQL stores conversations, preferences, evidence, task state, schedules,
actions and audit receipts. Markdown notes live in a persistent owner directory.
The host owner controls this storage. Processing is not local-only: selected
memory and conversation context goes to Nebius; research queries and configured
domains go to Tavily; approved issue content goes to GitHub.

Passwords use Argon2; browser sessions are opaque HttpOnly cookies, revoked on
logout and expired after 12 hours. Provider tokens are Fernet encrypted at rest.
ENCRYPTION_KEY stays outside PostgreSQL in .env.runtime or a secret manager.
This is not end-to-end encryption. Never lose that key without a recovery plan.
Revocation removes the stored credential and invalidates pending authority.

Memory deletion removes future active recall. There are no derived summaries or
search indexes to retain it. Prior messages and immutable run evidence may contain
the same information; delete the relevant conversation or retire the deployment
and its storage for a complete data purge. Export memory before deleting it when
needed. Do not use real private data for a public judge deployment.

Backup retention is operator controlled; suggested local policy is seven daily
backups, with encrypted offline storage and documented deletion. Deleting active
data does not erase historical backups. Rotate expired backups deliberately.
Application logs omit secrets, prompts and provider bodies. Diagnostic exports
should be reviewed before sharing.

## Enhancement scope and providers

A project-scoped memory is admitted only to that project's context; explicit
owner-wide preferences are shared across the owner's projects. Project facts do
not expand tool authority. Corrections preserve the original scope, and deletion
excludes the record from future recall; existing messages and backups remain.
There is currently no semantic index or background extraction service.

When explicitly selected, OpenAI or Anthropic receives the bounded conversation
and memory context instead of Nebius. Credentials remain write-only encrypted
records. OpenAI requests set `store=false`; this does not promise zero provider
retention. Provider terms and account policies still govern retained copies.
Markdown output does not load remote images automatically.

## Derived local memory index (optional enhancement)

When explicitly configured, admitted canonical memory is copied to a separate
private pgvector database as a bounded text prefix and a local E5 vector. No
embedding-provider API is used. Relevant canonical records may subsequently be
sent to the selected inference provider as context. Correction/deletion queues
index propagation; canonical retrieval excludes removed/expired records
immediately, even when propagation is pending. The index keeps text-free revision
tombstones to reject late writes. A newer correction can renew expired memory.

Outages may delay physical index removal. The Memory view reports pending and
failed updates. Operator backups can retain older copies under the configured
retention policy; deleting a current record does not erase historical backups or
previous conversation messages. The separate index database needs its own backup,
retention and restore procedures before production enablement.
