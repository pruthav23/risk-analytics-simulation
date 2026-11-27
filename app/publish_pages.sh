#!/usr/bin/env bash
# Rebuild Risk Desk and publish it to the gh-pages branch (served by GitHub Pages at
# https://pruthav23.github.io/risk-analytics-simulation/).
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON=$(command -v python3 || command -v python)
"$PYTHON" app/build.py

tmp=$(mktemp -d)
git fetch -q origin +refs/heads/gh-pages:refs/remotes/origin/gh-pages
git worktree add -q --detach "$tmp" origin/gh-pages
cp app/index.html "$tmp/index.html"
(
  cd "$tmp"
  git add index.html
  if git diff --cached --quiet; then
    echo "Live page already up to date."
  else
    git commit -q -m "Update Risk Desk"
    git push -q origin HEAD:gh-pages
    echo "Published. GitHub Pages refreshes within a minute or two."
  fi
)
git worktree remove --force "$tmp"
