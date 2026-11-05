# Vultr verification

## Current repair cycle — 2026-11-05

Implementation source: `8ab487716b1d73395dca49fd87db1a5e54fa7821`, branch
`vultr`. `main` remains `005deba0b0ee7a5c36bb57304bf0d542b5842005`.
Terminal Git push is working. The older sections below retain historical outcomes.

### Repairs and evidence

- **Implemented / Locally verified:** narrowly admit the two trusted sandbox
  image sources into Docker context. The actual build-context regression uses
  fictional private-file canaries, including nested environment files. An initial
  over-broad inclusion failed the canary and was corrected before publication.
- **Implemented / Locally verified:** isolate each Playwright test client in the
  disposable API server. Production ignores the test header and retains the
  10-per-minute login limit. Two PostgreSQL/API regressions test both properties.
  Eleven logins in the original fast CI suite exceeded the shared bucket; a
  controlled burst reproduced the 11th-login 429. The original CI trace was not
  retained, so its precise HTTP response was not observed. CI now uploads traces.
- **Implemented / Locally verified:** browser seccomp returns ENOSYS for denied
  `clone3` so libc can use permitted `clone`, and allows Chromium to chroot within
  its own user namespace. The outer unprivileged process still cannot chroot.
  No capabilities, host mounts, privileged mode or Chromium sandbox bypass added.
  A fixed offline browser test exercises thread creation, namespace confinement
  and cleanup before the existing restricted-gateway test.
- **Locally verified:** first repaired full gate: 176 Python tests passed, three
  opt-in container tests skipped, 90.64% coverage; 11 Chromium scenarios passed.
  The final candidate adds a fourth opt-in container test.
- **Locally verified:** [final release CI](https://github.com/RafalW3bCraft/TheCommander/actions/runs/42054356203)
  passed on `8ab4877`: 176 passed, four container tests explicitly skipped in this
  job, 90.52% coverage, 11 browser scenarios, static/build/audit/secret gates.
  The separate containment job executes those four skipped tests for real.
- **Locally verified:** [Docker/runc containment CI](https://github.com/RafalW3bCraft/TheCommander/actions/runs/42054356178)
  passed all four real tests in 9.73 seconds, both image builds and context canaries.
  This is not gVisor or Vultr-host evidence. The earlier
  [failed browser containment run](https://github.com/RafalW3bCraft/TheCommander/actions/runs/42052553383)
  is preserved as the pre-seccomp-repair result.
- **Locally verified:** disposable backup/restore and clean-source Compose
  startup/recreation passed. Local container engine is Podman, not Docker Engine.
  An earlier clean-release process ended with exit 143; its successful repeat
  does not erase that process anomaly.
- **Locally verified:** Python and memory-service audits report no known findings;
  production npm dependencies report none. Compatible tooling updates reduced
  development findings to seven moderate advisories; these remain unresolved.
- **Locally verified:** actual desktop, tablet, mobile, Settings and disconnected
  screenshots inspected; sandbox approval screenshots also inspected. Automated
  accessibility checks are separate from manual visual inspection. No independent
  accessibility certification, screen-reader audit or approved visual baseline.

The actual local `./scripts/verify.sh` also passed on the final implementation
with Node 22 and the disposable PostgreSQL 17 URL: exit 0, 319.203 seconds.
See `evidence/vultr-nov05-final-candidate-process.json` and its complete log.

### Live integrations and account gates

- **Live verified:** bounded Nebius evaluation 30/30 fictional cases, 28,057 tokens,
  zero unknown-usage cases. Tavily validation/search returned five persisted
  sources in 2,737 ms. These do not prove Vultr or a new GitHub write. Python
  documentation sources included newer versions than the application runtime;
  source usefulness/version alignment still needs human judgment.
- **Blocked:** real Vultr completion returned HTTP 401 (`invalid_credentials`).
  A catalog of 35 models was returned; catalog visibility is not authentication
  or model capability proof. Text, tools and image-input acceptance remain unpassed.
- **Blocked:** official Vultr CLI 3.11.0 was checksum-verified and used for a
  read-only lookup of the selected existing instance; the API returned HTTP 401.
  No resources were changed or provisioned. Keep a separate Compute CLI credential
  outside the application environment; app `VULTR_API_KEY` is for inference.
- **Blocked:** SSH host identity has not been confirmed through the trusted
  console. The supplied public key matches the local key; installation on the VM
  is unconfirmed. Obtain the server Ed25519 SHA256 fingerprint from its console.
- **Blocked:** `APP_DOMAIN` and a public HTTPS origin are absent. The Vultr noVNC
  URL is a private management console, not an application hostname.
- **Not run:** remote deployment, gVisor probes, live Vultr text/tool/vision flows,
  controlled-site human-approved browser write, and a new approved GitHub write.
  Preserve previous issue authority; it does not authorize another test issue.

Private `.env` and `.env.runtime` are unchanged and mode 0600. Configured:
`VULTR_API_KEY`, `ENCRYPTION_KEY`, `BOOTSTRAP_TOKEN`, `POSTGRES_PASSWORD`,
`NEBIUS_API_KEY`, `GITHUB_TOKEN`, `GITHUB_REPOSITORY`, `TAVILY_API_KEY`. Missing:
`PROVIDER_MODEL`, `SANDBOX_MODEL`, `SANDBOX_VISION_MODEL`, `APP_DOMAIN`.
The existing unsupported `SESSION_SECRET` was left untouched. No conflicting
file key names were found. Sandbox execution remains disabled; provider defaults,
saved settings, historical runs and encrypted records were not rewritten.

### Evidence and limits

Dated `evidence/vultr-nov05-*` files contain commands, process exits, source HEAD,
latency/usage and limitations. A diff hash is not a complete artifact identity;
the final release manifest supplies per-file hashes and archive SHA-256. Historic
evidence was retained separately rather than relabeled as current.

The applicable ECC verification-loop and security-review guidance was applied;
no catalog changes, native hooks or independent review execution are claimed.

The current [event brief](https://lablab.build/ai-hackathons/vultr-hackathon),
rechecked November 5, requires Challenge 1 Vultr inference and sandbox execution
on Vultr, a public demo, source/setup, recorded demonstration and a containment
moment. The [rule book](https://lablab.build/hackathon-rules) and relocated
[submission guide](https://lablab.build/delivering-your-hackathon-solution) were
also rechecked. The standard guide allows MP4/MOV up to 300 MB, recommends under
five minutes and calls for PDF slides; the actual event form takes precedence.
Authenticated form limits and existing-project eligibility remain unconfirmed. No enrollment, organizer
ruling, uploaded video, final submission or acceptance is claimed.

Local review materials: [draft slides](evidence/vultr-nov05-slides-draft.pdf),
[16:9 draft cover](evidence/vultr-nov05-cover-draft.png), and editable
[slide source](evidence/vultr-nov05-submission-draft.html). These explicitly mark
pending deployment and live gates; they are not a genuine final demo recording.

**Production-ready: no. Submission-ready: no.** Remote credentials/access,
hostname, gVisor and live inference, human-approved browser effects, judge access,
eligibility and genuine final media remain release gates.

## Historical verification — 2026-11-04

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
