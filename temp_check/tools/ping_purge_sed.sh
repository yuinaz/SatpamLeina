#!/usr/bin/env bash
set -e
# Purge any literal "auto-learn ping" strings in-place (Git Bash-safe)
ROOT="${1:-.}"
grep -RIl --null -E '\(auto-?learn ping\)' "$ROOT" | while IFS= read -r -d '' f; do
  sed -i 's/(auto-learn ping)//g' "$f"
  sed -i 's/🤖  *//g' "$f"
done
echo "Purge done."
