# ECC setup

Updated 2026-10-24. There are two distinct development surfaces; neither is
application runtime code. Full inventory: [ECC application ledger](ECC_APPLICATION.md)
and [catalog artifact](evidence/ecc-catalog.json).

## Current project installation

The owner installed `.agents/` during this session. Its preserved
`ecc-install-state.json` identifies **Antigravity project**, profile **full**,
version **2.2.0**, installed at `2026-10-24T00:17:32.489Z`. The receipt's source
commit is null; no commit provenance beyond that receipt is claimed. The inventory
found 276 skills and 693 total catalog/supporting files, including agents, rules,
workflows and the receipt. The host now exposes these skills in its catalog.

The receipt selects the full module set and skips hooks-runtime, media-generation
and orchestration. No installer was stacked over this installation. No user
catalog files, model settings, reasoning settings, permissions or hooks were
rewritten. Antigravity installation is not evidence of a native Codex plugin or
Claude hook support. Applying a skill means reading and using its relevant
guidance, not executing every example or installing every service it mentions.

## Original engineering reference

Reviewed 2026-10-22 against https://github.com/affaan-m/ECC.
Source pin: `90606c8315ee09cafc303515c5f33024db6b9882`; package version `2.2.3`.
Route: project-local adaptation, using the full official source checkout under
ignored `.tools/ecc`. Reproduce with `./scripts/setup_ecc.sh`.

At the original inspection, no `codex` executable was on PATH and no existing ECC
installation was found in the host skill catalog. Official `check-plugin-cache.js` reported no
cached ECC manifest; see evidence/ecc-plugin-diagnostic.txt. Native plugin
installation/diagnostics cannot be claimed. No legacy sync, global configuration
merge, MCP installation or hook activation was performed. No model, reasoning,
approval or sandbox setting was changed. Full source is available on demand;
the original session manually read selected skills. The later host-discovered
`.agents` catalog is described above; the two versions must not be conflated.

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
browser sign-off is claimed. A subsequent click-path reviewer supplied five
state-race findings. Its follow-up documentation turn hit a host usage limit;
the primary agent completed fixes, browser regressions and the report.
Development ECC memory/permissions are separate
from application owner data and action authority.

Source documentation: [Codex guidance](https://github.com/affaan-m/ECC/blob/90606c8315ee09cafc303515c5f33024db6b9882/.codex/AGENTS.md),
[full profile](https://github.com/affaan-m/ECC/blob/90606c8315ee09cafc303515c5f33024db6b9882/manifests/install-profiles.json).
