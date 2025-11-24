#!/usr/bin/env python3
# Offline XP readiness smoke (no network, no Discord login)
import json, pathlib, re, py_compile

ROOT = pathlib.Path(__file__).resolve().parents[1]
OVR = ROOT / "data" / "config" / "overrides.render-free.json"
COGS = ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs"
LADDER = ROOT / "data" / "neuro-lite" / "ladder.json"

def ok(x): return f"[OK]  {x}"
def warn(x): return f"[WARN]{x}"
def fail(x): return f"[FAIL]{x}"

def load_overrides():
    if not OVR.is_file(): return {}
    try: return json.loads(OVR.read_text(encoding="utf-8"))
    except Exception: return {}

def compile_if_exists(path):
    try:
        py_compile.compile(str(path), doraise=True)
        print(ok(f"compile {path.relative_to(ROOT)}"))
        return True
    except Exception as e:
        print(fail(f"compile {path.relative_to(ROOT)}: {e}"))
        return False

def main():
    print("====== XP OFFLINE SMOKE ======")
    # check mirror/recompute cogs (optional)
    c1 = COGS/"a08_xp_event_dual_mirror_bridge.py"
    c2 = COGS/"a08_xp_stage_recompute_overlay.py"
    if c1.is_file(): compile_if_exists(c1)
    else: print(warn("a08_xp_event_dual_mirror_bridge.py not found"))
    if c2.is_file(): compile_if_exists(c2)
    else: print(warn("a08_xp_stage_recompute_overlay.py not found"))

    ov = load_overrides()
    env = ov.get("env", {})

    # pin IDs check
    pin_ch = str(env.get("XP_PIN_CHANNEL_ID", "")).strip().strip('"').strip("'")
    pin_ms = str(env.get("XP_PIN_MESSAGE_ID", "")).strip().strip('"').strip("'")
    if re.fullmatch(r"\d{10,22}", pin_ch): print(ok(f"XP_PIN_CHANNEL_ID={pin_ch}"))
    else: print(warn(f"XP_PIN_CHANNEL_ID invalid -> '{pin_ch}'"))
    if re.fullmatch(r"\d{10,22}", pin_ms): print(ok(f"XP_PIN_MESSAGE_ID={pin_ms}"))
    else: print(warn(f"XP_PIN_MESSAGE_ID invalid -> '{pin_ms}'"))

    # ladder exists
    if LADDER.is_file():
        try:
            js = json.loads(LADDER.read_text(encoding="utf-8"))
            assert "senior" in js
            print(ok("ladder.json valid"))
        except Exception as e:
            print(fail(f"ladder.json invalid: {e}"))
    else:
        print(warn("ladder.json not found (will use defaults at runtime)"))

    print("====== DONE ======")

if __name__ == "__main__":
    main()
