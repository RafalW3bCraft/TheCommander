#!/usr/bin/env bash
# Fast-forward only the existing vultr branch; never overwrite/diverge/force-push.
set -euo pipefail
if [ "$#" -ne 1 ]; then
  printf 'Usage: %s /absolute/path/TheCommander-vultr-upgrade.bundle\n' "$0" >&2
  exit 2
fi
bundle_path=$(realpath "$1")
if [ "$(git branch --show-current)" != vultr ]; then
  printf 'Refusing: the current branch must already be vultr.\n' >&2
  exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
  printf 'Refusing: preserve/commit your current work before importing the bundle.\n' >&2
  exit 1
fi
if [ "$(git config --get remote.origin.url)" != 'https://github.com/RafalW3bCraft/TheCommander.git' ] &&
   [ "$(git config --get remote.origin.url)" != 'git@github.com:RafalW3bCraft/TheCommander.git' ]; then
  printf 'Refusing: origin is not the expected TheCommander repository.\n' >&2
  exit 1
fi
git bundle verify "$bundle_path"
git fetch "$bundle_path" refs/heads/vultr
git merge --ff-only FETCH_HEAD
printf 'Applied to vultr. Review, run the documented release gates, then publish with:\n  git push origin HEAD:refs/heads/vultr\n'
