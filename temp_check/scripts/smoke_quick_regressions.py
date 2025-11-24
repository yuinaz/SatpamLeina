
#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

must_exist = [
    ROOT/"satpambot/bot/modules/discord_bot/cogs/a00_fix_curriculum_autoload_path_overlay.py",
    ROOT/"satpambot/bot/modules/discord_bot/cogs/a00_fix_qna_autolearn_interval_overlay.py",
    ROOT/"satpambot/bot/modules/discord_bot/cogs/a08_xp_event_bridge_overlay.py",
    ROOT/"satpambot/bot/modules/discord_bot/cogs/a00_00_xp_kv_selfheal_overlay.py",
    ROOT/"satpambot/bot/modules/discord_bot/cogs/qna_answer_award_xp_overlay.py",
]

bad = False
for p in must_exist:
    if not p.exists():
        print(f"[FAIL] missing file: {p}")
        bad = True

def has(path, needle):
    try:
        return needle in path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False

bridge = must_exist[2]
selfheal = must_exist[3]
award = must_exist[4]

if not has(bridge, "_coerce_key_numeric(") or not has(bridge, "_smart_coerce("):
    print("[FAIL] event_bridge overlay missing numeric auto-coerce helpers")
    bad = True
if not has(selfheal, "_smart_coerce("):
    print("[FAIL] xp selfheal overlay missing smart coercion")
    bad = True
if not has(award, 'cfg_str("XP_SENIOR_KEY", "xp:bot:senior_total")'):
    print("[FAIL] qna_answer_award_xp_overlay default key is not xp:bot:senior_total")
    bad = True

if bad:
    sys.exit(1)
print("OK")
