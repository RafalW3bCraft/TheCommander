# Baseline

Checked 2026-11-16 from uid 1001. The git checkout `/mnt/hostshare/TheCommander` is owned by uid 1000, mode 755. A write probe returned `Permission denied`. `git status` there is clean on branch `vultr`.

- `HEAD`: `50f7c0cee8ef5e09a9046c18b81479f1d043d92a`
- `origin/main` and `origin/HEAD`: same SHA
- `origin/vultr`: `08dc39fde04c3917da32d6bb86b4ff2caf219f5d` (local `vultr` is two merge commits ahead)
- Local branch `main`: `005deba0b0ee7a5c36bb57304bf0d542b5842005`, 17 commits behind `origin/main`

Edits are only in `/home/watcher/tc-work/TheCommander`. The lifecycle patch was applied from `/home/watcher/tc-lifecycle-patch/tc-lifecycle-relative.diff` before further changes. No commit, push, or deploy.

Toolchain in this session: Python 3.13.5, Node v20.19.2, npm 9.2.0, PostgreSQL 17. `uv` is not on `PATH`. Frontend `package.json` asks for Node `>=22.12.0 <23`. The original `.venv` is executable and was used as the pytest/mypy/ruff interpreter. Frontend `node_modules` in the copy is a symlink to the checkout install.
