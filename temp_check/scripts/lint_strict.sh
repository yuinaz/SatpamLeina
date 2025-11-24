#!/usr/bin/env bash
set -euo pipefail
CFG="ruff.toml"
python - <<'PY'
import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('ruff') else 1)
PY
|| { echo "[!] install ruff: python -m pip install -U ruff"; exit 1; }
python -m ruff check . --config "$CFG"
