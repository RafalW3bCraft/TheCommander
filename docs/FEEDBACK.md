# Observed technology feedback

Nebius Token Factory: the configured NVIDIA Nemotron model appeared in the account
model list. A real bounded smoke request returned a valid function call, and a
follow-up accepted its result. Actual usage and latency are in live-smoke.json.
The compatible API works for this tested subset; this does not prove all OpenAI
features are supported. Missing/truncated/malformed results fail visibly.

NVIDIA model: nvidia/nemotron-3-super-120b-a12b was exercised for tool proposal and
continuation. No broad model-quality benchmark or training claim is made.

Tavily: the existing configured key passed live validation on 2026-10-27. An authorized
broker search restricted to docs.python.org returned four persisted evidence items
in 5,622 ms. Results included different documentation versions/languages, so domain
filtering alone does not ensure relevance. No currency cost is claimed.

GitHub: adapter and controlled failure contracts implemented. Live provider
experience remains untested: token is a placeholder and no repository is selected.
No fabricated product feedback is offered for GitHub.

ECC: pinned reference 2.2.3 and installed catalog 2.2.0 were used as documented
project-local guidance. Installed Codex tooling does not establish native hook
parity or execution of every catalog entry; see ECC_SETUP.md.

Local environment: PostgreSQL at port 5433 was initially available, later stopped;
verification moved to a separate cluster rather than modifying existing data.
Docker was a Podman wrapper requiring its user socket to be started.

Latest model acceptance run: 2026-10-27 UTC, 30/30 cases, 29 calls, 27,974
reported tokens. Alternate model selection is validated before saving; unavailable
models fail visibly. Pricing stays unknown unless supplied by the operator.

Observed October 27 limitation: one live tool-result continuation returned an
invalid completion and was rejected. An unchanged diagnostic rerun and a separate
30-task application evaluation passed. The original response shape/root cause
was not captured; no provider fix or uninterrupted reliability is claimed.
