# Product requirements

An owner should be able to remember a preference once, return in a new session,
run a useful engineering task, and inspect what happened while away.

- AUTH-01: Bootstrap once, log in/out, keep sessions server-side; reject other owners.
- MEM-01: Create/search/correct/delete/export preferences with provenance and revisions.
- CHAT-01: Persist conversations and include active preferences in real inference.
- INF-01: Use an NVIDIA model through Nebius; bounded requests and honest failures.
- CON-01: Set/test/update/revoke encrypted connections with factual status and scope.
- ACT-01: Preview exact issue arguments, approve once, verify an external receipt.
- SKILL-01: Engineering briefing collects repository and approved research evidence.
- SKILL-02: Research to action prepares a specific issue with an approval gate.
- SKILL-03: Follow-through saves a useful next-step note from persistent context.
- JOB-01: Durable one-shot/elapsed-interval schedules run without an open browser.
- REC-01: Leases, cancellation, deduplication, recovery and uncertain-write reconciliation.
- FILE-01: Owner-scoped safe Markdown files with durable receipts.
- UI-01: Five navigable, responsive destinations with keyboard and error states.
- OPS-01: Reproducible startup, migrations, backups, verification and bounded logging.

Acceptance is behavior through the actual API/database/UI. Mocked vendor success
is only contract-test evidence; external verification is a distinct release gate.
