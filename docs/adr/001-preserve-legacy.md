# ADR 001 — preserve legacy code and data, isolate the release

Accepted 2026-10-22. The baseline Flask application exposes broad command routes,
uses process-local state and provider fallbacks. Incrementally exposing those
routes would retain unacceptable authority boundaries. Build a FastAPI release
package and React UI without importing legacy modules.

Keep root legacy files, MIT notices, `schema.sql`, `.env`, the modified
`env.example`, and both instruction documents. Place new tables in `commander`
rather than altering existing `public` records. Import is explicit and dry-run
first. This adds a migration boundary but preserves the owner's work and avoids
unverified data transformations. The new release uses only `uv.lock` and the
frontend npm lock; old `requirements.txt` describes the unserved legacy app.
