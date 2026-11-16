# Architecture map

React/Vite UI in `frontend/src` talks to the same-origin FastAPI app in `commander/api.py` and `commander/routes.py`. PostgreSQL is the authority. `commander/worker.py` heartbeats, recovers expired leases, dispatches due schedules, and claims one queued run per owner.

| Journey | Entry | Authority |
|---|---|---|
| Bootstrap, sign-in, sign-out | `frontend/src/main.tsx` | `commander/api.py`, `commander/auth.py` |
| Projects and conversations | `ProjectSelector.tsx`, Assistant in `main.tsx` | `commander/projects.py`, `commander/runs.py` |
| Mode | Composer select | `commander/modes.py` rejects `build` and `review` |
| Model and provider status | `SettingsPage.tsx`, `ConnectionsPage` | `commander/preferences.py`, `commander/connections.py` |
| Memory | `MemoryPage`, `MemorySearch.tsx` | `commander/memory.py`, owner predicate on every query |
| Tool approval | `ActionCard`, `SandboxPage.tsx` | `commander/broker.py`, `commander/sandbox/service.py` |
| Schedules | Schedule panel | `commander/schedules.py` `dispatch_due` |
| Cancel | Run details and the new deny button | `commander/runs.py` `cancel` |
| Provider failure | Worker tick | `commander/engine.py` raises before HTTP when the connection is missing |

A model tool call is allowed only when `modes.permitted` includes it. Ask mode permits no tools. Cancellation updates a run only while it is still `queued`, `running`, `waiting_approval`, or `uncertain`, and denies pending actions in that same transaction. Memory reads and exports filter on `owner_id`.

Schedules that are due while `max_daily_runs` is already spent move `next_at` forward by `BUDGET_BACKOFF` (five minutes) and do not insert a run. The next worker tick does not lock them again until that time.
