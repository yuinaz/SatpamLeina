
#!/usr/bin/env bash
set -euo pipefail

PY="python"

# Prefer requirements.latest.txt if present
REQ="requirements.txt"
if [[ -f "requirements.latest.txt" ]]; then
  REQ="requirements.latest.txt"
fi

echo "[build] using $REQ"
$PY -m pip install --upgrade pip setuptools wheel
$PY -m pip install -r "$REQ"

# show brief env
$PY - <<'PYCODE'
import importlib, pkgutil, sys
mods = ["discord", "flask", "aiohttp", "httpx", "groq", "numpy", "psutil", "PIL"]
for m in mods:
    try:
        mod = importlib.import_module(m)
        ver = getattr(mod, "__version__", getattr(getattr(mod, "version", None), "__version__", "unknown"))
        print(f"{m:<10} : {ver}")
    except Exception as e:
        print(f"{m:<10} : ERR({e.__class__.__name__})")
PYCODE
