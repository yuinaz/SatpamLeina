
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QNA OFFLINE SMOKE (clean version)"""

import os, json, pathlib, re

# ---------- Pretty printers ----------
def ok(msg): print(f"[OK]  {msg}")
def warn(msg): print(f"[WARN]{msg}")
def head(title): print(f"==[{title}]==")

# ---------- Load/merge overrides ----------
OV = pathlib.Path("data/config/overrides.render-free.json")
env = {}
try:
    env = json.loads(OV.read_text(encoding="utf-8")).get("env", {})
    for k, v in env.items():
        if k not in os.environ or os.environ[k] == "":
            os.environ[k] = str(v)
    print(f"[env] merged from {OV}")
except Exception as e:
    print(f"[env] merge failed: {e}")
    env = {}

print("====== QNA OFFLINE SMOKE ======")

# ---------- COG presence / compile ----------
head("cogs")
A24 = pathlib.Path("satpambot/bot/modules/discord_bot/cogs/a24_qna_auto_answer_overlay.py")
A06 = pathlib.Path("satpambot/bot/modules/discord_bot/cogs/a06_autolearn_qna_answer_overlay.py")

def _compile(p):
    try:
        compile(p.read_text(encoding="utf-8"), str(p), "exec")
        ok(f"compile {p.as_posix()}")
    except Exception as e:
        warn(f"compile fail {p.name}: {e}")

if A24.is_file():
    ok(f"{A24.name} present")
    _compile(A24)
else:
    warn(f"missing {A24.as_posix()}")

if A06.is_file():
    ok(f"{A06.name} present")
    _compile(A06)
else:
    warn(f"missing {A06.as_posix()}")

# ---------- QNA env ----------
head("QNA env")
def getenvk(k, default=""): return os.getenv(k, default)
def show(k): print(f"  {k}={getenvk(k)}")
for k in ("QNA_ENABLE","QNA_CHANNEL_ID","QNA_INTERVAL_SEC","LLM_GEMINI_MODEL","LLM_GROQ_MODEL"):
    show(k)

# ---------- a24 embed titles ----------
head("a24 embed titles")
src = A24.read_text(encoding="utf-8") if A24.is_file() else ""
m1 = re.search(r"QNA_EMBED_TITLE_PROVIDER\s*=\s*(.+)", src)
m2 = re.search(r"QNA_EMBED_TITLE_LEINA\s*=\s*(.+)", src)

def _print_val(name, match):
    if match:
        ok(f"{name} -> {match.group(1).strip()}")
        return True
    val = env.get(name) or os.getenv(name)
    if val:
        ok(f"{name} (env) -> {val}")
        return True
    warn(f"{name} not found")
    return False

got1 = _print_val("QNA_EMBED_TITLE_PROVIDER", m1)
got2 = _print_val("QNA_EMBED_TITLE_LEINA", m2)

prov_val = (m1.group(1) if m1 else (env.get("QNA_EMBED_TITLE_PROVIDER") or os.getenv("QNA_EMBED_TITLE_PROVIDER") or ""))
if prov_val and "{provider}" not in str(prov_val):
    warn("Provider title does not contain {provider}")
else:
    ok("Provider title contains {provider}")

# ---------- scheduler ----------
head("scheduler")
SCH = pathlib.Path("satpambot/bot/modules/discord_bot/cogs/a24_qna_autolearn_scheduler.py")
if SCH.is_file():
    txt = SCH.read_text(encoding="utf-8", errors="ignore")
    if "QNA_CHANNEL_ID" in txt:
        ok("uses QNA_CHANNEL_ID")
    else:
        warn("scheduler does not reference QNA_CHANNEL_ID")
    _compile(SCH)
else:
    warn(f"missing {SCH.as_posix()}")

print("====== DONE ======")
