# Branch-only handoff

**Publication update — 2026-11-05:** The implementation is now published on the
remote `vultr` branch through the GitHub integration. Terminal Git publication was subsequently verified on November 5; see
[Vultr verification](VULTR_VERIFICATION.md) for the current source and CI evidence. `main` is unchanged. The integration publishes a consolidated
commit containing the reviewed local source and permission bits; its commit ID
can differ from the earlier local five-commit history.

The original bundle below preserves that pre-publication local history. Keep it
as a recovery artifact; do not apply it on top of the published implementation.
For a checkout still at the old remote baseline, fetch `origin vultr` and perform
a fast-forward only. If you already imported the old bundle, compare source trees
and preserve local work before reconciling the different commit histories.

The remainder of this document records the earlier, blocked-publication handoff.

The delivered Git bundle contains **only the new `vultr` commits**, with that
baseline as a prerequisite. Download it outside your existing checkout, verify
that checkout has the baseline, and preserve any uncommitted work first. The
included `scripts/apply_vultr_bundle.sh` checks the current branch, clean worktree,
repository identity and bundle prerequisites, then performs a fast-forward only.
It refuses a divergent branch and never force-pushes.

If that helper is not yet in your existing checkout, use these commands from the
`vultr` branch, replacing `bundle_path` with the actual downloaded file path:

```sh
bundle_path=/absolute/path/TheCommander-vultr-upgrade.bundle
test "$(git branch --show-current)" = vultr
test -z "$(git status --porcelain)"
git bundle verify "$bundle_path"
git fetch "$bundle_path" refs/heads/vultr
git merge --ff-only FETCH_HEAD
```

This preserves commit identity and affects no other branch. If the fast-forward
fails because someone advanced `vultr`, inspect both histories and integrate only
on `vultr`; do not overwrite concurrent work. The separate patch is a review and
recovery alternative, not a second change to apply after importing the bundle.

After write access is available and the commits are reviewed:

```sh
git push origin HEAD:refs/heads/vultr
```

Then review **Verify release** and **Vultr sandbox containment** Actions runs. New
workflow files may need GitHub integration permission to write workflows in
addition to repository contents. Nothing in this handoff grants those external
permissions. Never paste a token into chat or a tracked file.

Continue with [the release prompt](VULTR_CODEX_PROMPT.md), [deployment/submission guide](VULTR_GUIDE.md)
and [honest verification status](VULTR_VERIFICATION.md). No deployment, enrollment,
public demo URL, successful live Vultr call or final submission is claimed.
