# Observed technology feedback

Nebius Token Factory: the configured NVIDIA Nemotron model appeared in the account
model list. A real bounded smoke request returned a valid function call, and a
follow-up accepted its result. Actual usage and latency are in live-smoke.json.
The compatible API works for this tested subset; this does not prove all OpenAI
features are supported. Missing/truncated/malformed results fail visibly.

NVIDIA model: nvidia/nemotron-3-super-120b-a12b was exercised for tool proposal and
continuation. No broad model-quality benchmark or training claim is made.

GitHub and Tavily: adapters and controlled failure contracts implemented. Live
provider experience is untested until real credentials/scopes are configured.
No fabricated product feedback is offered for these providers.

ECC: official source and catalog were usable for project-local guidance, but the
host had no Codex CLI/native ECC plugin cache. Hook parity was not assumed.

Local environment: PostgreSQL at port 5433 was initially available, later stopped;
verification moved to a separate cluster rather than modifying existing data.
Docker was a Podman wrapper requiring its user socket to be started.
