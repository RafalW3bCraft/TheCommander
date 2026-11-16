# Implementation plan

Done in `/home/watcher/tc-work/TheCommander` only.

1. Apply `tc-lifecycle-relative.diff` (TC-001 through TC-004).
2. Reproduce the missing schedule `queued` event and the hot due-row when the daily budget is spent. Both assertions failed on the unfixed scheduler.
3. Defer a budget-blocked schedule by `BUDGET_BACKOFF` (five minutes), increment revision, and leave `last_at` and `paused` unchanged. Write `queued` only when an insert returns an id.
4. Show validation field errors, cap invitation and bootstrap tokens at 200 characters, and require the operator password before environment import.
5. Add "Deny and stop this run" on a pending GitHub proposal. It calls the existing cancel route.
6. Add `scripts/evaluate_offline.py` for tool selection, cancellation, and memory isolation with fixtures.
7. Record the current git refs in `docs/VULTR_VERIFICATION.md` without restating unverified deploy results.

Not done, and not safe to invent:

- Node 22 install, `./scripts/verify.sh`, and Playwright.
- Live Nebius, Vultr, OpenAI, Anthropic, Tavily, or GitHub calls.
- Public HTTPS and gVisor.
- Applying the diff to `/mnt/hostshare/TheCommander` (permission denied for uid 1001).
