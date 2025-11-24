
import json, sys
from _smoke_common import ensure_sys_path, load_overrides

root = ensure_sys_path()
doc, path_used = load_overrides()
env = doc.get("env", {}) if isinstance(doc, dict) else {}

hot_boot   = env.get("HOTENV_RELOAD_ON_BOOT","0") == "0"
hot_start  = env.get("HOTENV_AUTORELOAD_ON_STARTUP","0") == "0"
watch_glob = env.get("HOTENV_WATCH_GLOBS","").strip() != ""
overlay1 = "satpambot.bot.modules.discord_bot.cogs.a00_qna_provider_autofailover_quota_overlay"
overlay2 = "satpambot.bot.modules.discord_bot.cogs.a00_channel_policy_gate_overlay"
always = env.get("COGS_ALWAYS","") + "," + env.get("COGS_ALWAYS+","")
overlay_in_always = all([o in [x.strip() for x in always.split(",") if x.strip()] for o in (overlay1, overlay2)])

catmap = env.get("HOTENV_CATEGORY_MAP_JSON","{}")
try:
    catmap_obj = json.loads(catmap) if isinstance(catmap, str) else (catmap or {})
except Exception:
    catmap_obj = {}
overlay_in_qna = overlay1 in catmap_obj.get("QNA", []) if isinstance(catmap_obj, dict) else False

print("[HOTENV file]", path_used or "(not found)")
print("[HOTENV ok flags]", hot_boot, hot_start)
print("[HOTENV watch_globs]", bool(watch_glob))
print("[HOTENV overlay always]", overlay_in_always)
print("[HOTENV overlay QNA-map]", overlay_in_qna)

if not all([hot_boot, hot_start, bool(watch_glob), overlay_in_always]):
    sys.exit(2)
