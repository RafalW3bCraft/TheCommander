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
