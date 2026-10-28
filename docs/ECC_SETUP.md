# ECC setup

Updated 2026-10-28. There are two distinct development surfaces; neither is
application runtime code. Full inventory: the applicability ledger below
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
coverage is recorded in RELEASE_REPORT.md. Browser delegation failed due to host usage
limits, so browser work was continued by the primary agent; no independent
browser sign-off is claimed. A subsequent click-path reviewer supplied five
state-race findings. Its follow-up documentation turn hit a host usage limit;
the primary agent completed fixes, browser regressions and the report.
Development ECC memory/permissions are separate
from application owner data and action authority.

Source documentation: [Codex guidance](https://github.com/affaan-m/ECC/blob/90606c8315ee09cafc303515c5f33024db6b9882/.codex/AGENTS.md),
[full profile](https://github.com/affaan-m/ECC/blob/90606c8315ee09cafc303515c5f33024db6b9882/manifests/install-profiles.json).

## Applicability and artifact ledger

All **276 installed skills** and **693 supporting files** are inventoried in
[ecc-catalog.json](evidence/ecc-catalog.json), including each skill description,
content hash, applicability status and evidence links. This is a complete catalog
inventory, not a claim that every workflow was executed. Examples for unrelated
languages, finance, healthcare, publishing, networking or external services are
not application requirements and do not grant external-action authority.

The pinned reference additionally contains **311 canonical skills** and **4,627
tracked files**, inventoried in [ecc-reference-inventory.json](evidence/ecc-reference-inventory.json).
Thirty-six reference skills are absent from the older installation, while its
`motion-ui` entry is absent from the newer canonical catalog. Both versions are
preserved; availability and application are recorded independently.

Reproduce locally: `uv run python -m scripts.audit_repository`. The script also
produces [recursive-inventory.json](evidence/recursive-inventory.json), containing
source classifications, imports, route handlers, dependencies and duplicate hashes.
It reads local files only; it does not run catalog scripts or upload source.

| Applied guidance | Concrete artifact or change |
|---|---|
| configure-ecc | [Setup/provenance](ECC_SETUP.md), pinned reference and full-profile plan |
| tdd-workflow, ai-regression-testing | Red/green audit evidence; malformed-provider, permission, context, recovery and UI-race regressions |
| verification-loop | [Verification script](../scripts/verify.sh), [audit gate log](evidence/cleanup-verification.txt) |
| fastapi-patterns, api-design, contract-first | Pydantic response contracts, OpenAPI and generated TypeScript; authenticated routes and visible errors |
| postgres-patterns, database-migrations | Owner constraints, durable worker transitions, additive message/run migration and backup/restore drill |
| security-review | [Findings](RELEASE_REPORT.md), [threat model](THREAT_MODEL.md), approval/citation/secret boundaries |
| frontend-patterns | Stable effects, revision-bound forms, guarded asynchronous responses, session expiry handling |
| e2e-testing, browser-qa | Chromium workflows, delayed-response tests, desktop/tablet/mobile screenshots, axe checks |
| click-path-audit | [State and route traces](TRACEABILITY.md), five reviewer findings and fixes |
| agent-architecture-audit | [Twelve-layer report](evidence/agent-architecture-audit.json) |
| eval-harness | [Evaluation protocol and limits](RELEASE_REPORT.md), actual Nebius acceptance runs |
| production-audit | [Recursive audit and readiness assessment](RELEASE_REPORT.md), [release report](RELEASE_REPORT.md) |
| module-regression, change-impact (pinned reference) | [Downstream acceptance ledger](TRACEABILITY.md), post-change source/data/interface/release impact alignment in the audit and ADRs |

These are adapted engineering workflows. A complete native slash-command run,
every checklist item, independent reviewer sign-off, or host hook activation is
not implied by the word “applied.” Evidence records the exact checks performed.

The remaining catalog entries have explicit non-execution statuses:

- `repo-scan` is a bootstrap pointer, not an installed scanner. Its external
  installer was not run; the repository inventory is our local script.
- `delivery-gate` is a Claude Stop hook. It was reviewed but not activated in this
  Codex host; project verification remains explicit and reproducible.
- `agent-eval` compares coding agents. It is not the application's live model
  acceptance evaluation and was not reported as such.
- `skill-stocktake` informed the catalog inventory only. No full per-skill quality,
  freshness or usage-frequency audit was performed. `config-gc` is for Claude
  configuration cleanup; the owner’s installed catalog was retained intact.
- Other skills are available references, catalogued but not invoked for this
  FastAPI/PostgreSQL/React task. Their descriptions and hashes remain reviewable.

Development artifacts are separate from application memory, tool permissions and
secrets. Neither ECC catalog is included in the production image. The user-owned
Antigravity 2.2.0 installation and pinned 2.2.3 reference are recorded separately.


## October 28 cleanup application

The user selected retention of the complete versioned catalog. All 693 installed
artifacts and 276 skills are preserved byte-for-byte. TDD, security-review and
verification-loop guidance informed isolation/packaging regressions, hashed
preservation, dependency tracing and final release checks. Red/green evidence is
in cleanup-safety-red.txt and cleanup-safety-green.txt. Existing uncommitted work
is preserved; checkpoint evidence uses logs and an archive rather than commits
over the owner’s changes. This pass is self-review, without new subagents,
installers, native hooks or unrelated skill execution.
