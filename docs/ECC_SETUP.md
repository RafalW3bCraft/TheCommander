# ECC setup

Reviewed 2026-10-22 against https://github.com/affaan-m/ECC.
Source pin: `90606c8315ee09cafc303515c5f33024db6b9882`; package version `2.2.3`.
Route: project-local adaptation, using the full official source checkout under
ignored `.tools/ecc`. Reproduce with `./scripts/setup_ecc.sh`.

Host inspection: no `codex` executable on PATH. No existing ECC installation was
found in the host skill catalog. Official `check-plugin-cache.js` reported no
cached ECC manifest; see evidence/ecc-plugin-diagnostic.txt. Native plugin
installation/diagnostics cannot be claimed. No legacy sync, global configuration
merge, MCP installation or hook activation was performed. No model, reasoning,
approval or sandbox setting was changed. Full source is available on demand;
this session manually reads selected skills rather than claiming auto-discovery.

Read official README, `.codex/AGENTS.md`, Codex navigation, full install manifest,
installer help and plan. `full` already contains core; there was no stacked
full/core installation. See evidence/ecc-full-plan.json. Native Codex hooks are
a narrower reviewed subset requiring host trust, not Claude hook parity.

Applied relevant guidance: tdd-workflow, verification-loop, fastapi-patterns,
postgres-patterns, security-review, frontend-patterns, api-design and e2e-testing;
shared Python/security/testing rules. These names exist in the pinned source.
An independent bounded security-review role reported six findings; regression
coverage is recorded in FINDINGS.md. Browser delegation failed due to host usage
limits, so browser work was continued by the primary agent; no independent
browser sign-off is claimed. Development ECC memory/permissions are separate
from application owner data and action authority.

Source documentation: [Codex guidance](https://github.com/affaan-m/ECC/blob/90606c8315ee09cafc303515c5f33024db6b9882/.codex/AGENTS.md),
[full profile](https://github.com/affaan-m/ECC/blob/90606c8315ee09cafc303515c5f33024db6b9882/manifests/install-profiles.json).
