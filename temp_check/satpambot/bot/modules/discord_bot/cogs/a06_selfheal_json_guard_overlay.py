from __future__ import annotations

import json, re, logging
log = logging.getLogger(__name__)
def _strip_fences(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"```\s*$", "", s)
    return s.strip()
def _repair(s: str) -> str:
    s = _strip_fences(s)
    m = re.search(r"\{[\s\S]*\}", s)
    if m: s = m.group(0)
    s = s.replace("\r","").replace("\t","\n")
    s = re.sub(r"//.*?$", "", s, flags=re.MULTILINE)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
    s = re.sub(r'(?m)(^|[,{\s])([A-Za-z_][A-Za-z0-9_\-]*)\s*:', r'\1"\2":', s)
    s = re.sub(r"(?<!\\)'", '"', s)
    s = re.sub(r'\bTrue\b', 'true', s)
    s = re.sub(r'\bFalse\b', 'false', s)
    s = re.sub(r'\bNone\b', 'null', s)
    s = re.sub(r",\s*([}\]])", r"\1", s)
    return s.strip()
def parse_plan(text: str):
    err = None
    for attempt in range(3):
        try:
            s = text if attempt==0 else _repair(text)
            return json.loads(s)
        except Exception as e:
            err = e
    log.warning("[selfheal_json_guard] failed to parse plan: %s ...snippet=%r", err, (text or "")[:200])
    return None
def _install():
    try:
        mod = __import__("satpambot.bot.modules.discord_bot.cogs.selfheal_groq_agent", fromlist=["*"])
    except Exception as e:
        log.debug("[selfheal_json_guard] import agent failed: %s", e); return
    setattr(mod, "parse_plan", parse_plan)
    if hasattr(mod, "SAFE_PARSE_PLAN"): setattr(mod, "SAFE_PARSE_PLAN", parse_plan)
    log.info("[selfheal_json_guard] installed")
_install()

# ---- auto-added by patch: async setup stub for overlay ----
async def setup(bot):
    return