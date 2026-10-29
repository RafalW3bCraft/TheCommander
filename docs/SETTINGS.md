# Owner settings and execution policy

The supported configuration UI is Settings → Connections / Model and limits /
Data and privacy / System. Infrastructure environment variables remain operator
controlled; the browser never exposes an arbitrary environment editor.

Authenticated GET/PATCH `/api/settings` returns preferences, effective values,
operator ceilings and a revision. PATCH requires that revision and rejects stale
edits with 409. Connection PUT accepts revision 0 for a new connection and requires
the current revision for updates. An empty credential preserves the secret only
while the locked current connection remains active; explicit revocation clears it.
Reload the affected form after a conflict. Changing credentials invalidates validation.

The additive migration 004 creates owner_settings and adds a nullable JSON run
snapshot. Existing installations keep their data. Interactive runs snapshot at
enqueue; schedule occurrences snapshot at dispatch. Legacy queued runs with a null
snapshot resolve current owner settings. Every inference dispatch applies the
stricter of snapshot, current owner and operator limits. Skill step/time ceilings
also apply. Operator changes require restarting API and worker. Existing running
HTTP calls are bounded by network timeouts, not immediately aborted by cancellation.

GET `/api/models?provider=nebius` lists account-visible NVIDIA models from the
saved allowed endpoint. Model/endpoint edits require discovery and a small live
inference before saving; failure leaves the previous settings unchanged. A changed
model must be revalidated after replacing its credential. Only the two documented
Token Factory endpoint origins are accepted. There is no provider/model fallback.
Unknown usage or pricing remains unknown. Operator pricing applies only to the
operator model; alternate models have unknown pricing and cannot dispatch with a
spend cap until appropriate operator configuration is supplied.

GET `/api/system/status` requires authentication and shows database/API/worker
status and configuration-presence booleans. It never exposes the environment,
connection strings, encryption keys, bootstrap token or provider credentials.

Validation: tests/test_release_settings.py, frontend/e2e/workflows.spec.ts.

Migration 005 records each inference's conservative token reservation. A failed
request with unknown consumption retains its original reservation even after
owner limits decrease. Historical unknown rows receive the maximum supported
108192-token reservation until they age out of the rolling 24-hour window.
Known provider usage takes precedence. A lower setting cannot erase prior usage.

## Enhancement provider selection

`inference_provider` is `nebius`, `openai`, or `anthropic`. Nebius retains
`nebius_model` and its restricted endpoint choices. Optional APIs use an explicit
`provider_model` and fixed HTTPS origins. Configure their separate encrypted
credentials in Connections, discover account models, then save the chosen model.
Selection performs a live validation request and remains unchanged if validation
fails. API credentials are independent of consumer subscriptions.

Old runs retain their provider; no fallback occurs on errors, throttling or
revocation. Optional-provider pricing is unknown; a spending cap blocks those
requests until pricing support exists. Daily token reservations cover all providers.
Usage identifies both provider and model. No infrastructure secrets were rotated.

## Optional private memory index

`MEMORY_INDEX_URL` and `MEMORY_INDEX_TOKEN` are operator-only configuration. Both
are blank by default; the browser cannot configure a general network endpoint or
view the token. Use a private Compose service/loopback URL or operator-controlled
HTTPS; redirects and environment proxies are disabled. The separately selected
`deploy/compose.memory.yaml` requires independent database and service secrets.
It never inherits provider API credentials. See [ADR005](adr/005-memory-index.md).

Memory search reports disabled/degraded/ready retrieval separately from pending
synchronization, retry count and bounded-prefix indexing. These are operational
states, not claims of retrieval quality. Indexing is asynchronous while the worker
is idle; existing canonical preferences remain available during outages. Model
embeddings use up to 512 tokens of the first 4,000 characters. Canonical memory
retains its full text. Search queries may be shortened with an explicit indicator.
