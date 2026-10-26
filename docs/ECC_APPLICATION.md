# ECC application and artifact ledger

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
| verification-loop | [Verification script](../scripts/verify.sh), [audit gate log](evidence/audit-verification.txt) |
| fastapi-patterns, api-design, contract-first | Pydantic response contracts, OpenAPI and generated TypeScript; authenticated routes and visible errors |
| postgres-patterns, database-migrations | Owner constraints, durable worker transitions, additive message/run migration and backup/restore drill |
| security-review | [Findings](FINDINGS.md), [threat model](THREAT_MODEL.md), approval/citation/secret boundaries |
| frontend-patterns | Stable effects, revision-bound forms, guarded asynchronous responses, session expiry handling |
| e2e-testing, browser-qa | Chromium workflows, delayed-response tests, desktop/tablet/mobile screenshots, axe checks |
| click-path-audit | [State and route traces](CLICK_PATH_AUDIT.md), five reviewer findings and fixes |
| agent-architecture-audit | [Twelve-layer report](evidence/agent-architecture-audit.json) |
| eval-harness | [Evaluation protocol and limits](EVALUATION.md), actual Nebius acceptance runs |
| production-audit | [Recursive audit and readiness assessment](CODEBASE_AUDIT.md), [release report](RELEASE_REPORT.md) |
| module-regression, change-impact (pinned reference) | [Downstream acceptance ledger](REGRESSION.md), post-change source/data/interface/release impact alignment in the audit and ADRs |

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

## 2026-10-25 settings/release increment

Applied tdd-workflow, api-design, security-review and verification-loop guidance:
new PostgreSQL regression tests, explicit revision contracts, encrypted write-only
credentials, schema-generated frontend types, browser race reproduction, and the
complete release gate. The conversation regression was checked against the old
handler to prove that delayed history overwrites the selected conversation; the
fixed handler is then tested with the same assertion. See release-settings-red.txt,
release-settings-green.txt, conversation-race-red.txt and release-verification.txt.
Checkpoint evidence is recorded in artifacts; no automatic commits were made over
user-owned working-tree changes. This is an adapted workflow, not a claim of every
skill checklist or native hook execution. Review in this increment is self-review.
All unrelated skills remain inventoried, not executed or certified.

## 2026-10-26 continuation verification

Read and applied verification-loop and security-review guidance, with separate
self-review passes for authorization, scoped dispatch, persistent jobs, settings,
provider constraints and public errors. The user-requested red/green process
reproduced and repaired F15 (live probe process status). Evidence is
live-probe-red.txt, live-probe-green.txt and continuation-verification.txt.
The installed/pinned catalogs and all private configuration remain preserved;
no unrelated skill execution, independent agent review or native hook activation
is claimed. Prior evidence was copied before refresh; see continuation-baseline.json.
