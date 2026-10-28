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
5. Schedule Follow-through for the next minute. Close the browser; reopen Assistant
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

## Tested fictional acceptance example

The isolated October 28 acceptance used `AetherSilva/thecommander-acceptance`
(private), the NVIDIA Nemotron model documented in README, and `docs.python.org`
as the Tavily domain. The prompt `Python asyncio task cancellation official
documentation. Propose one documentation checklist issue for this fictional
acceptance-test repository.` produced a reviewable action. Its final title/body
were edited to label historical sources and avoid unsupported claims before one
approval created issue #1. The exact preview and receipt are in release evidence.
Do not replay that approval or assume authority to create another test issue.

The private repository is an acceptance resource, not a public source repository
or judge deployment. A reviewer needs an authorized GitHub website account to
view its receipt contents. Dedicated application credentials, accessible repository
scope, provider quota and availability through December 15 still need arranging.
Never include the owner's bootstrap token, provider key or private test password
in public instructions or the recording. Entrant eligibility remains unconfirmed.
