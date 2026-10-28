# Observed technology feedback

Nebius Token Factory: the configured NVIDIA Nemotron model appeared in the account
model list. A real bounded smoke request returned a valid function call, and a
follow-up accepted its result. Actual usage and latency are in live-smoke.json.
The compatible API works for this tested subset; this does not prove all OpenAI
features are supported. Missing/truncated/malformed results fail visibly.

NVIDIA model: nvidia/nemotron-3-super-120b-a12b was exercised for tool proposal and
continuation. No broad model-quality benchmark or training claim is made.

Tavily: the configured key passed live validation on 2026-10-28. A broker search
restricted to docs.python.org persisted five evidence items in 3,106 ms. Results
included historical and language-specific documentation; domain filtering alone
does not ensure relevance. A verbose workflow query produced no evidence and
failed honestly; a shorter query returned a proposal. Review sources against the
intended version and remove unsupported recommendations. No currency cost is claimed.

GitHub: with specific user authorization, created the private acceptance repository
and used the application to prepare/edit/approve exactly one issue. The worker
confirmed it, and a separate authenticated GET matched the exact approved body,
title and correlation marker. The receipt persisted across restart. Opening its
private URL without a GitHub website login shows not-found; judge access must
account for repository visibility. No ambiguous live write failure was injected.

ECC: pinned reference 2.2.3 and installed catalog 2.2.0 were used as documented
project-local guidance. Installed Codex tooling does not establish native hook
parity or execution of every catalog entry; see ECC_SETUP.md.

Local environment: PostgreSQL at port 5433 was initially available, later stopped;
verification moved to a separate cluster rather than modifying existing data.
Docker was a Podman wrapper requiring its user socket to be started.

Latest model acceptance run: 2026-10-28 UTC, 30/30 cases, 29 calls, 28,061
reported tokens. Alternate model selection is validated before saving; unavailable
models fail visibly. Pricing stays unknown unless supplied by the operator.

Observed October 27 limitation: one live tool-result continuation returned an
invalid completion and was rejected. An unchanged diagnostic rerun and a separate
30-task application evaluation passed. The original response shape/root cause
was not captured; no provider fix or uninterrupted reliability is claimed.

October 28 application defect: valid source URLs enclosed by Unicode citation
brackets were rejected by our parser. A failing regression reproduced this and a
narrow delimiter fix repaired it without permitting unknown URLs. The model's
successful briefing still contained broad cancellation advice unsupported by the
short evidence excerpt. Saved citations establish provenance, not entailment or
correctness; this acceptance set does not certify autonomous technical advice.
