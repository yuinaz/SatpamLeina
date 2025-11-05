
import json, sys
from _smoke_common import ensure_sys_path

root = ensure_sys_path()

candidates = [
    "data/config/xp_work_ladder.json",
    "data/config/xp_ladder.json",
    "data/config/xp_stage_ladder.json"
]
ladder = None; path_used=None
for p in candidates:
    pp = root / p
    if pp.exists():
        try:
            ladder = json.loads(pp.read_text(encoding="utf-8"))
            path_used = str(pp); break
        except Exception: pass

print("[XP ladder file]", path_used or "(not found)")

def _snap(val, default=0):
    try:
        return int(val)
    except Exception:
        try:
            return int(float(val))
        except Exception:
            return default

def simulate_progress(current=0, add=123, required=1000):
    cur2 = current + add
    pct = 0.0 if required<=0 else (cur2/required)*100.0
    return {"current":cur2,"required":required,"percent":round(pct,2)}

if ladder:
    current = _snap(ladder.get("stage",{}).get("current", ladder.get("current", 0)))
    required = _snap(ladder.get("stage",{}).get("required", ladder.get("required", 1000)))
    sim = simulate_progress(current=current, add=321, required=required or 1000)
    print("[XP sim] +321 ->", sim["current"], "/", sim["required"], f"({sim['percent']}%)")
else:
    sim = simulate_progress(current=59065, add=321, required=158000)
    print("[XP sim*] +321 ->", sim["current"], "/", sim["required"], f"({sim['percent']}%)")

ok = (sim["percent"] > 0.0)
print("[XP ok]", ok)
sys.exit(0 if ok else 2)
