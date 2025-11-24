#!/usr/bin/env bash
set -e
REPO="${1:-.}"
echo "== autofix v3 (oneliners/semicolons/EOF/trailing) =="
python scripts/auto_fix_lint_v3.py "$REPO"
echo "== ruff format =="
python -m ruff format "$REPO" || true
echo "== ruff fix (safe) =="
python -m ruff check "$REPO" --fix || true
echo "== ruff fix (unsafe) =="
python -m ruff check "$REPO" --fix --unsafe-fixes || true
echo "== ruff strict check =="
python -m ruff check "$REPO"
echo "All done."
