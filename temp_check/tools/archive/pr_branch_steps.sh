#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./pr_branch_steps.sh "<commit message>" [base_branch]
# Example:
#   ./pr_branch_steps.sh "feat(ui): login particles + dashboard & grep fixes" main

COMMIT_MSG="${1:-feat(ui): login particles + dashboard & grep fixes}"
BASE_BRANCH="${2:-main}"

# Ensure we're in a git repo
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "Not a git repo"; exit 1; }

# Pick base branch (main/master auto-fallback)
if ! git show-ref --verify --quiet "refs/heads/$BASE_BRANCH"; then
  if git show-ref --verify --quiet refs/heads/master; then BASE_BRANCH="master"; fi
fi

git fetch --all --prune
git checkout "$BASE_BRANCH"
git pull --rebase --autostash

# Create branch name
ts="$(date +%Y%m%d-%H%M)"
BRANCH="feat/ui-login-particles-grepfix-${ts}"

git checkout -b "$BRANCH"

# Stage everything (or limit to specific paths if needed)
git add -A

# If nothing to commit, continue gracefully
if git diff --cached --quiet; then
  echo "Nothing to commit. Proceeding to push current branch."
else
  git commit -m "$COMMIT_MSG"
fi

# Push and set upstream
git push -u origin "$BRANCH"

# Try to open PR via GitHub CLI if available
if command -v gh >/dev/null 2>&1; then
  echo "Creating PR via gh..."
  gh pr create --fill --base "$BASE_BRANCH" --head "$BRANCH" || true
else
  # Build compare URL
  REMOTE_URL="$(git config --get remote.origin.url)"
  # Normalize to https link
  if [[ "$REMOTE_URL" =~ ^git@([^:]+):([^/]+)/(.+)\.git$ ]]; then
    HOST="${BASH_REMATCH[1]}"; OWNER="${BASH_REMATCH[2]}"; REPO="${BASH_REMATCH[3]}"
    COMPARE_URL="https://${HOST}/${OWNER}/${REPO}/compare/${BASE_BRANCH}...${BRANCH}?expand=1"
  elif [[ "$REMOTE_URL" =~ ^https?://([^/]+)/([^/]+)/([^\.]+)(\.git)?$ ]]; then
    HOST="${BASH_REMATCH[1]}"; OWNER="${BASH_REMATCH[2]}"; REPO="${BASH_REMATCH[3]}"
    COMPARE_URL="https://${HOST}/${OWNER}/${REPO}/compare/${BASE_BRANCH}...${BRANCH}?expand=1"
  else
    COMPARE_URL="$REMOTE_URL"
  fi
  echo "Open this URL to create a PR:"
  echo "$COMPARE_URL"
fi

echo "Done. Branch: $BRANCH"
