# Vultr verification — 2026-11-04

**Publication update — 2026-11-05:** GitHub integration write access is available
again, and this implementation is published to `vultr` through the integration.
Terminal Git still lacks credentials. `main` is unchanged. Check the branch's
Actions runs for current CI results; PostgreSQL, Docker/gVisor, live Vultr and
public deployment remain release gates. The table below records the historical
2026-11-04 verification and the publication block observed then.
Baseline: `96fcd1f8fdd0d64ebba486acb67e2c56e5851b7a`.

| Gate | Actual result |
|---|---|
| Ruff check/format | Passed locally, including the sandbox driver/proxy |
| mypy | Passed, 32 source modules |
| React TypeScript + Vite production build | Passed; local Node 24.22.1, repository/CI target Node 22 |
| Frontend ESLint / Prettier | Passed |
| New policy/runner tests | 19 passed; offline contracts, not live containment |
| Trusted browser driver tests | 5 passed; controlled Playwright double, not live browser execution |
| Existing non-DB release tests | 10 passed |
| Combined Python check | **34 passed, 3 real-container tests skipped** |
| Real Chromium UI | **1 passed**: login fixture, project history, plan inspection, exact password-gated approval, receipt export, 1440 px desktop/390 px mobile, no horizontal overflow, axe checks in both layouts |
| UI evidence limits | Real Chromium 153 with mocked backend; not real API, PostgreSQL, sandbox execution or Vultr inference |
| Python dependency audit | No known vulnerabilities reported |
| Production frontend dependency audit | 0 vulnerabilities reported |
| All frontend dependency audit | No high findings; **13 moderate development-tool findings** associated with minimatch advisory GHSA-g3hv-75wg-m249 remain |
| Configured-secret scan | Passed; no configured private runtime values in source/bundle |
| Existing API paths | All preserved; 8 sandbox paths added |
| Source release packaging | Created; existing historical release manifest preserved, new manifest stored separately |
| PostgreSQL workflow tests | 11 new cases written; execution attempt stopped at startup/teardown with connection refused at 127.0.0.1:5433. No assertions ran; not a pass |
| Real Docker Python/browser tests | 3 explicit opt-in cases written; Docker executable/daemon unavailable locally |
| Real gVisor on Vultr | Not run |
| Real Vultr text/vision inference | Not run; credentials unavailable |
| Remote publication / CI | **Blocked**. Git push has no terminal credentials; GitHub connector rejects Git tree/blob/contents writes with HTTP 403 “Resource not accessible by integration.” No remote branch changed, no new CI run triggered |
| Public HTTPS demo, video/slides, final LabLab submission | Not completed |

The normal Playwright browser download returned truncated ZIP content. The UI-only
check used a separately unpacked npm-provided Chromium binary with software/GPU
rendering disabled in an ignored local harness. This did not change the production
browser driver, its required Chromium sandbox, gVisor selection, dependency locks
or real-container CI tests. A UI-only Playwright config is included for normal
machines; the default browser suite still uses the real API/PostgreSQL test server.

The 13 moderate findings affect development dependencies. The upstream advisory,
[published October 27 and updated October 30, 2026](https://github.com/advisories/GHSA-g3hv-75wg-m249),
identifies minimatch before 11.0.1. A forced transitive major override was not
applied: old ESLint/tool consumers need compatibility validation. These findings
remain a hardening item, rather than being described as fixed.

## Preservation and review

No existing private `.env` or key file was changed or created. The checked-in
example only adds opt-in fields. Old providers/defaults, runtime structure,
owner/session/memory/project behavior and baseline API paths remain present.
Existing evidence files were not overwritten. Approval evidence now retains the
original screenshot/URL, plan, domains and runtime so it remains inspectable after
execution. Read-only browser completion also requires a final goal-verification
call, rather than equating “page visible” with “task done.”

The implementation is **not yet production-ready or submission-ready**. To unblock:
review both CI workflows on the published `vultr` branch; run PostgreSQL 17, actual Docker/gVisor and
Vultr text/vision gates; deploy on Vultr; obtain the existing-project ruling;
produce genuine media and submit through the actual LabLab form.
