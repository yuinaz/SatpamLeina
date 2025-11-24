#!/usr/bin/env bash
set -e
REPO="${1:-.}"
echo "== auto-fix (E701/E702 + EOF newline) =="
python scripts/auto_fix_lint_v2.py "$REPO"
echo "== ruff format =="
python -m ruff format "$REPO" || true
echo "== ruff fix (safe) =="
python -m ruff check "$REPO" --fix || true
echo "== ruff fix (unsafe; may remove unused imports) =="
python -m ruff check "$REPO" --fix --unsafe-fixes || true
echo "== ruff check (strict) =="
python -m ruff check "$REPO"
echo "All done."
