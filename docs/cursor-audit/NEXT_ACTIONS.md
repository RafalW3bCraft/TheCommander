# Next actions

The git checkout at `/mnt/hostshare/TheCommander` is still clean. Apply the diff as uid 1000. Do not commit unless Art asks.

```bash
cd /mnt/hostshare/TheCommander
git apply /home/watcher/tc-work/thecommander-fixes.diff
```

Then, still on a disposable database:

```bash
TEST_DATABASE_URL="postgresql://$(id -un)@127.0.0.1:55432/postgres" \
  uv run pytest -q --cov=commander --cov-report=term-missing
uv run mypy commander
cd frontend && npm ci && npm run lint && npm run build
# Optional offline browser suite (Node 22 + uv):
TEST_DATABASE_URL="postgresql://$(id -un)@127.0.0.1:55432/postgres" \
  npm run test:e2e
```

Remaining blockers for a stronger classification:

- Live Nebius / Vultr / OpenAI / Anthropic / Tavily / GitHub credentials for a bounded smoke (optional; offline e2e already covers fixture paths).
- Public HTTPS and production cookie/HSTS settings.
- gVisor (`runsc`) sandbox execution.
- Node 22 for `./scripts/verify.sh` and Playwright CI parity.
- `./scripts/test_db.sh` until `.runtime/` is writable by the user who runs it.
- Realtime duplex voice remains out of scope; browser STT/TTS only.

Optional product follow-ups:

- Hold-to-talk UX polish if Web Speech interim results feel noisy on some browsers.
- Submit credential import once with a recent password on a machine that has server env secrets.
