#!/usr/bin/env python3
# QNA SMOKE v3 — inline path fixer
import os, sys, importlib
from pathlib import Path

# --- PATH FIXER (inline) ---
HERE = Path(__file__).resolve()
CANDIDATES = [HERE.parent] + list(HERE.parents)[1:6]  # scripts/, repo root, ...
added=None
for base in CANDIDATES:
    if (base / "satpambot").is_dir():
        sys.path.insert(0, str(base))
        added = base
        break
    if (base / "src" / "satpambot").is_dir():
        sys.path.insert(0, str(base / "src"))
        added = base / "src"
        break
# --- END PATH FIXER ---

print("[QNA SMOKE v3] starting")
def sh(v): 
    return (v[:12] + ("..." if len(v)>12 else "")) if v else "<unset>"

keys = ["QNA_CHANNEL_ID","GROQ_API_KEY","GROQ_MODEL","GEMINI_API_KEY","GEMINI_MODEL","OPENAI_BASE_URL"]
for k in keys:
    print(f"{k}= {sh(os.getenv(k))}")

# Info path
print("[sys.path][0] =", sys.path[0])
if added:
    print("[pathfix] added =", added)

# Try import satpambot
try:
    importlib.import_module("satpambot")
    print("[import] satpambot OK")
    mods = [
        "satpambot.bot.modules.discord_bot.cogs.neuro_autolearn_moderated_v2",
        "satpambot.bot.modules.discord_bot.cogs.a06_autolearn_qna_answer_overlay",
        "satpambot.bot.modules.discord_bot.cogs.a24_qna_dedup_guard_overlay",
        "satpambot.bot.modules.discord_bot.cogs.a24_qna_dual_provider_runtime_overlay",
    ]
    for m in mods:
        try:
            importlib.import_module(m)
            print("[import]", m, "OK")
        except Exception as e:
            print("[import]", m, "FAIL:", e)
except Exception as e:
    print("[import] satpambot FAIL:", e)
    print("[hint] Jalankan dari folder yang punya 'satpambot/', atau set PYTHONPATH ke root repo.")
print("[QNA SMOKE v3] done")
