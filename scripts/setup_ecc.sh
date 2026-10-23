#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
commit=90606c8315ee09cafc303515c5f33024db6b9882
if [ ! -d .tools/ecc/.git ]; then
  mkdir -p .tools
  git clone --no-checkout https://github.com/affaan-m/ECC.git .tools/ecc
  git -C .tools/ecc checkout --detach "$commit"
fi
if [ "$(git -C .tools/ecc rev-parse HEAD)" != "$commit" ]; then
  printf 'Existing ECC checkout differs from reviewed pin; preserving it.\n' >&2
  exit 1
fi
node .tools/ecc/scripts/install-plan.js --profile full --target codex --json > docs/evidence/ecc-full-plan.json
printf 'Full pinned ECC source available at .tools/ecc. No native hooks or user configuration changed.\n'
