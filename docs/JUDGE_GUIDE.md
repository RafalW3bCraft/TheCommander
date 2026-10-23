# Judge guide (local draft)

Use a dedicated test deployment and fictional data, never the owner's real account.
There is no published deployment or judge credential in this repository.

1. Follow README startup; create a dedicated owner account.
2. Configure Nebius with the NVIDIA model and test it. Select a disposable GitHub
   repository with Issues read/write permission and configure Tavily approved domains.
3. Enable workspace notes. Save preference `Briefing format`: `Use three short
   bullets and source links` in Memory.
4. Run Engineering briefing with `Review retry-handling improvements`. Inspect
   timestamped evidence and the saved Markdown note.
5. Schedule Follow-through for the next minute. Close the browser; reopen Today
   after the worker runs. Check status, result and note receipt in Activity.
6. Start a new conversation and request your saved briefing format. Memory should
   be present in the actual model context after restarting API/worker as well.
7. Run Research to action. Review repository, exact title/body and approval expiry.
   Only approve a disposable repository write that you intend to create. Open the
   verified GitHub receipt after worker execution.
8. Inspect failure/cancellation behavior. Revoke a connection before approving a
   pending proposal; the old authority must not execute. Unsupported shell tools
   are rejected by the broker even if a model proposes them.

Offline tests deliberately use labeled vendor fixtures. They are not a substitute
for judge-facing live integrations. See release report for exact remaining blockers.
