# ADR 004 — Retire unsupported source after preservation

Accepted 2026-10-28 under the owner's approved cleanup plan. Supersedes the
working-tree retention portions of ADR001/002; their historical reasoning remains.

The supported Python import graph has no edges to the old root modules or agents.
The container allowlist excludes the Flask runtime, templates and static assets.
Retire those files, redundant setup manifests and superseded documentation.
Preserve their exact pre-change bytes in a hashed ignored archive and record each
removal in docs/evidence/cleanup-removals.json. Git history remains unchanged.

Keep the supported root launcher, all five migrations, the independent legacy JSON
importer, original MIT notices, all 693 versioned ECC artifacts and both installed/
pinned ECC provenance records. No user data, public-schema tables, private
environment, runtime key, volume or historical Git object is removed.

Twelve canonical documents replace overlapping status/specification reports.
Stable requirement/finding IDs and unique regression/failure evidence survive the
consolidation. Evidence is pruned by supersession, never by filename extension.
Final acceptance requires the complete local gate and a regenerated, verified
artifact. GitHub live workflows, remote deployment and submission remain separate.
