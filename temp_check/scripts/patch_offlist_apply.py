#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, json, sys, pathlib

def info(msg): print("[INFO]", msg)
def ok(msg): print("[OK] ", msg)
def warn(msg): print("[WARN]", msg)

OV = pathlib.Path("data/config/overrides.render-free.json")
if not OV.is_file():
    warn(f"Overrides file not found: {OV}")
    sys.exit(1)

data = json.loads(OV.read_text(encoding="utf-8"))
env = data.get("env", {})

env.setdefault("QNA_TITLE_ISOLATION", "Answer by Leina")
env.setdefault("QNA_EMBED_TITLE_PROVIDER", "Answer by {provider}")
env.setdefault("QNA_EMBED_TITLE_LEINA", "Answer by Leina")

env["SHADOW_ENABLE"] = "1"
env.setdefault("SHADOW_SKIP_IDS", "")
env.setdefault("LEARNING_SKIP_CHANNEL_IDS", "")
env.setdefault("DISABLE_DUPLICATE_QNA", "1")

raw = env.get("COGS_ALWAYS", "") or ""
mods = [m.strip() for m in raw.split(",") if m.strip()]

off_exact = set([
    "satpambot.bot.modules.discord_bot.cogs.a00_render_runtime_guard",
    "satpambot.bot.modules.discord_bot.cogs.a00_hotenv_autoreload_overlay",
])
shadow_main = "satpambot.bot.modules.discord_bot.cogs.a08_shadow_learning_observer_overlay"
shadow_alt  = "satpambot.bot.modules.discord_bot.cogs.a08s_shadow_learning_observer_overlay"

seen = set()
clean = []
for m in mods:
    if m in seen: continue
    seen.add(m); clean.append(m)

clean2 = [m for m in clean if m not in off_exact]
if shadow_main in clean2 and shadow_alt in clean2:
    info("Both shadow observers found; keeping main and removing alt.")
    clean2 = [m for m in clean2 if m != shadow_alt]

env["COGS_ALWAYS"] = ",".join(clean2)
data["env"] = env
OV.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
ok("overrides.render-free.json updated.")

UC = pathlib.Path("satpambot/bot/modules/discord_bot/helpers/upstash_client.py")
if UC.is_file():
    txt = UC.read_text(encoding="utf-8")
    def inject_guard(func_name, text):
        sig = f"async def {func_name}("
        i = text.find(sig)
        if i == -1:
            return text, 0
        j = text.find("\n", i)
        if j == -1:
            return text, 0
        k = j + 1; indent = ""
        while k < len(text) and text[k] == " ":
            indent += " "; k += 1
        if "skip (shutting down)" in text[i:i+400]:
            return text, 0
        guard = (
            f"{indent}import os\n"
            f"{indent}if os.getenv('LEINA_SHUTTING_DOWN') == '1':\n"
            f"{indent}    try:\n"
            f"{indent}        log\n"
            f"{indent}    except Exception:\n"
            f"{indent}        import logging as _lg; log=_lg.getLogger(__name__)\n"
            f"{indent}    log.warning('[upstash-client] skip (shutting down) {func_name.upper()}')\n"
            f"{indent}    return None\n"
        )
        return text[:j+1] + guard + text[j+1:], 1
    txt2, c1 = inject_guard("_aget", txt)
    txt3, c2 = inject_guard("_apost", txt2)
    changed = c1 + c2
    if changed:
        UC.write_text(txt3, encoding="utf-8")
        ok(f"upstash_client.py guarded in {changed} function(s).")
    else:
        info("upstash_client.py already has shutdown guards.")
else:
    warn(f"helpers/upstash_client.py not found: {UC}")

def patch_graceful(path):
    P = pathlib.Path(path)
    if not P.is_file(): warn(f"graceful file not found: {P}"); return
    t = P.read_text(encoding="utf-8")
    if "LEINA_SHUTTING_DOWN" in t: info(f"{P.name} already sets shutdown flag."); return
    if "import os" not in t.splitlines()[:40]: t = "import os\n" + t
    new = re.sub(r"(async\s+def\s+shutdown\s*\([^)]*\)\s*:\s*)",
                 r"\1\n        os.environ['LEINA_SHUTTING_DOWN'] = '1'\n",
                 t, flags=re.M)
    if new != t: P.write_text(new, encoding="utf-8"); ok(f"{P.name}: set LEINA_SHUTTING_DOWN at shutdown entry.")
    else: info(f"{P.name}: no 'shutdown(...)' found to patch.")
patch_graceful("satpambot/bot/modules/discord_bot/cogs/a00_graceful_shutdown_overlay.py")
patch_graceful("satpambot/bot/modules/discord_bot/cogs/graceful_shutdown.py")

def neutralize_shadow(path):
    P = pathlib.Path(path)
    if not P.is_file(): return 0
    t = P.read_text(encoding="utf-8"); changed = 0
    pat = re.compile(r"try:\s*\n\s*qna\s*=\s*int\([^)]*QNA_CHANNEL_ID[^)]*\)[\s\S]*?except\s+Exception:\s*pass", re.M)
    t2 = re.sub(pat, "try:\n    pass\nexcept Exception:\n    pass", t)
    if t2 != t: changed += 1; t = t2
    if "LEINA PATCH: allow award in QNA channel" not in t:
        t += ("\n# --- LEINA PATCH: allow award in QNA channel (explicit-only skip) ---\n"
              "try:\n"
              "    import os\n"
              "    _qna = int(os.getenv('QNA_CHANNEL_ID','0'))\n"
              "    if _qna:\n"
              "        for _n in ['SKIP','SKIP_IDS','SKIP_CHANNELS']:\n"
              "            if _n in globals():\n"
              "                _s = globals()[_n]\n"
              "                try:\n"
              "                    _s.discard(_qna)\n"
              "                except Exception:\n"
              "                    try:\n"
              "                        if _qna in _s: del _s[_qna]\n"
              "                    except Exception:\n"
              "                        pass\n"
              "except Exception:\n"
              "    pass\n"
              "# --- /LEINA PATCH ---\n")
        changed += 1
    if changed: P.write_text(t, encoding="utf-8"); ok(f"{P.name}: neutralized auto-skip (changes={changed}).")
    else: info(f"{P.name}: no auto-skip detected."); return changed

neutralize_shadow("satpambot/bot/modules/discord_bot/cogs/a08_shadow_learning_observer_overlay.py")
neutralize_shadow("satpambot/bot/modules/discord_bot/cogs/a08s_shadow_learning_observer_overlay.py")

ok("ALL DONE. Re-run smoke: resolver/markers/shadow/shutdown should be green.")
