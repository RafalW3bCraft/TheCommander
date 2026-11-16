# Feature parity (evidence-based)

Compared to typical public ChatGPT / Claude / Grok *client* capabilities.
Marks reflect this repository and local verification, not scraped proprietary UIs.

| Capability | ChatGPT / Claude / Grok (typical) | TheCommander | Status |
|---|---|---|---|
| Text chat / Ask | Live model replies | Ask/Plan/Research/Automate modes; SSE run events (progress, not token stream) | **Implemented** (live reply needs configured inference) |
| Projects / workspaces | Project-scoped chats | Projects with default + scoped memory/runs | **Implemented** |
| Memory | Long-term user memory | Explicit memory CRUD, export, project scope, expiry | **Implemented** |
| Tool use | Browse, code, files, connectors | Skill tools + GitHub issue proposal + notes + research; sandbox gated | **Partial** (sandbox/browser modes disabled in UI until available) |
| Approvals for side effects | Varies | Exact-hash GitHub issue approval; Deny-and-stop cancels the run | **Implemented** |
| Scheduling | Custom GPTs / scheduled tasks (product-dependent) | Cron-like schedules with budget backoff | **Implemented** |
| Voice input (STT) | Live / push-to-talk to model | Browser Web Speech dictation into the existing prompt → run pipeline | **Partial** (browser STT only; no realtime voice session) |
| Voice output (TTS) | Spoken replies / live mode | Local `speechSynthesis` read-aloud; clear unavailable state otherwise | **Partial** (no server TTS; no live duplex voice) |
| Live voice / realtime duplex | ChatGPT Voice, Claude voice (where offered), Grok voice | Not present; architecture excludes server voice pipelines | **Missing / out-of-scope** |
| Multi-agent swarms | Limited / product-specific | Explicitly out of scope | **Out-of-scope** |
| Billing / subscriptions | Native | Not in product | **Out-of-scope** |
| Model marketplace UI | Provider pickers | Connections + Discover models (live validation) | **Partial** (needs live provider keys) |

## Voice vs ChatGPT / Claude / Grok

- **ChatGPT / Claude / Grok:** continuous or session-based voice modes with cloud STT/TTS (and often barge-in).
- **TheCommander:** opt-in **Dictate** fills the prompt; **Read aloud** uses the browser when available. Mic permission and missing-API states are explicit. Dictation does not enable Build/Review/sandbox tools.
- **Not claimed:** realtime conversational voice, Whisper server, or paid speech providers.

Evidence: `frontend/src/voice.ts`, `frontend/src/VoiceControls.tsx`, Assistant `Composer` in `frontend/src/main.tsx`, `docs/ARCHITECTURE.md`.
