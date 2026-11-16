# Verification report

Disposable database: `postgresql://watcher@127.0.0.1:55432/postgres`, data directory `/tmp/tc-pg-work`. Stopped after the browser pass. This is not the application database. `DATABASE_URL` was unset for pytest.

Offline browser stack: `scripts.e2e_server` on `http://127.0.0.1:8010` (MockTransport vendor; seeded `browser-owner` / `fictional-browser-password`). No paid provider spend.

## Commands and results

Targeted regressions (voice surface + lifecycle + offline eval + schedule backoff): exit 0, 4 passed.

`/mnt/hostshare/TheCommander/.venv/bin/mypy commander`: exit 0, 38 files.

Full suite, exit 0:

```
217 passed, 6 skipped, 88.54% coverage, 273.40s
```

Frontend, from `frontend/` with existing `node_modules`, Node v20.19.2: Prettier, eslint on voice files + `main.tsx`, `tsc --noEmit`, Vite build exit 0. Bundle `dist/assets/index-amvVMFtu.js`.

Playwright suite and `./scripts/verify.sh` were not run (Node 22 / `uv` gate). An assertion for **Start dictation** was added to `frontend/e2e/workflows.spec.ts`.

## Browser (cursor-ide-browser, click-through)

| Journey | Result | Evidence |
|---|---|---|
| Sign-in / session restore | **Verified** | Login → Assistant; reload kept session |
| Sign-out / sign-in | **Verified** | Welcome back → login → Assistant again |
| Create project | **Verified** | `Fictional notes` in project select |
| Ask-mode task (offline fixture) | **Verified** | Succeeded with fixture reply; run detail opened |
| Voice Dictate | **Verified** | Start/Stop dictation; network error copy when STT service failed; prompt pipeline unchanged |
| Voice Read aloud | **Verified** | Button on assistant reply; browser TTS path |
| Settings connections copy | **Verified** | Status guide; badges `Ready` / `Not set up yet` |
| Model discovery | **Verified** | “1 models available for nebius” via offline transport |
| Memory create / edit / delete | **Verified** | Briefing length create → correct → delete empty |
| Approval Deny | **Verified** | Research-to-action → Deny and stop → `cancelled` |
| Approval Approve | **Verified** | Second research-to-action → Approve → Open verified issue link |
| Schedules create/list | **Verified** | Schedule submitted; Edit/Pause/Delete visible |
| Mobile viewport (390×844) | **Verified** | Session restore + Dictate still present; metrics cleared |
| Credential import submit | **Partial** | Password gate visible; not submitted (no server env secrets) |
| Live paid providers | **Blocked** | Offline mocks only |
| Playwright / verify.sh / gVisor / HTTPS | **Blocked** | Toolchain / deploy gates |

## Release classification

**Locally functional** (stronger evidence than prior pass: offline successful model replies, approve/deny click-through, voice UX, schedules, memory edit/delete).

Not Production verified. Not integration with live Nebius/OpenAI/Anthropic/Vultr. Not public HTTPS. Not gVisor.
