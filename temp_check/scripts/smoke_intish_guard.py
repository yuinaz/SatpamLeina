#!/usr/bin/env python3
import os, sys, json, pathlib
def _ensure_sys_path():
    here = pathlib.Path(__file__).resolve()
    for p in [here.parent, here.parent.parent, here.parent.parent.parent]:
        sat = p / "satpambot"
        if sat.exists() and sat.is_dir():
            sys.path.insert(0, str(p)); return True
    return False
_found = _ensure_sys_path()
try:
    from satpambot.bot.modules.discord_bot.helpers.intish import parse_intish  # type: ignore
except Exception:
    def parse_intish(raw):
        if raw is None: return (False, None)
        if isinstance(raw, int): return (True, int(raw))
        s = str(raw).strip()
        if s == "": return (False, None)
        try: return (True, int(s))
        except Exception: pass
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                for k in ("senior_total_xp","total","value","v","xp","count"):
                    if k in obj:
                        try: return (True, int(obj[k]))
                        except Exception: continue
            if isinstance(obj, int): return (True, int(obj))
        except Exception: pass
        return (False, None)
cases = ["324550", '{"senior_total_xp": 324550}', '{"value": "324550"}', '{"total": 324550, "junk": "x"}', "  324550  ", "invalid", ""]
print("# satpambot import path detected:", _found)
for c in cases:
    ok, v = parse_intish(c); print(f"{c!r} -> ok={ok}, value={v}")