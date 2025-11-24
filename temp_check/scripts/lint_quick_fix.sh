#!/usr/bin/env bash
set -euo pipefail
CFG="ruff.toml"
if ! python - <<'PY'
import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('ruff') else 1)
PY
then
  python -m pip install -U ruff
fi
python -m ruff format . --config "$CFG" || true
python -m ruff check . --config "$CFG" --select I --fix || true
python -m ruff check . --config "$CFG" --fix || true
if [[ "${1:-}" == "--unsafe" ]]; then python -m ruff check . --config "$CFG" --fix --unsafe-fixes || true; fi
echo "[✓] Quick lint fix done."
