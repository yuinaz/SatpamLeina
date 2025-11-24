#!/usr/bin/env python3
import json, sys, os, re
from pathlib import Path

PATH = Path("data/config/overrides.render-free.json")
CHID = os.getenv("PATCH_QNA_CH_ID", "1426571542627614772")
INTERVAL = os.getenv("PATCH_QNA_INTERVAL", "180")

if not PATH.exists():
    print(f"[FAIL] {PATH} not found", file=sys.stderr)
    sys.exit(1)

raw = PATH.read_text(encoding="utf-8", errors="ignore")
try:
    data = json.loads(raw)
except Exception as e:
    print(f"[FAIL] JSON parse error: {e}", file=sys.stderr)
    sys.exit(2)

env = data.get("env") or {}
if not isinstance(env, dict):
    print("[WARN] 'env' not a dict; reinitializing to {}", file=sys.stderr)
    env = {}
    data["env"] = env

# Normalize channel id (strip accidental quotes) then set to desired one
def norm_id(s):
    if s is None:
        return None
    t = str(s).strip()
    # remove wrapping quotes like "\"12345\"" or "'12345'"
    if len(t) >= 2 and ((t[0] == t[-1] == '"') or (t[0] == t[-1] == "'")):
        t = t[1:-1]
    t = t.replace('"','').replace("'",'')
    return t

# Update keys ONLY, keep the rest intact
env["QNA_CHANNEL_ID"]  = norm_id(CHID) or "1426571542627614772"
env["QNA_INTERVAL_SEC"] = str(int(INTERVAL))  # ensure numeric string

# Write backup + file
backup = PATH.with_suffix(PATH.suffix + ".bak")
backup.write_text(raw, encoding="utf-8")
PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

print("[OK] Patched:", {"QNA_CHANNEL_ID": env["QNA_CHANNEL_ID"], "QNA_INTERVAL_SEC": env["QNA_INTERVAL_SEC"]})
print("[OK] Backup :", backup)
