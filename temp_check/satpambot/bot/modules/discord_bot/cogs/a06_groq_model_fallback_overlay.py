from __future__ import annotations

import logging, os
from satpambot.config.local_cfg import cfg
log = logging.getLogger(__name__)
def _candidates():
    raw = cfg("GROQ_MODEL_CANDIDATES", "") or ""
    xs = [x.strip() for x in raw.replace(",", " ").split() if x.strip()]
    return xs or [os.getenv("GROQ_MODEL","llama-3.1-8b-instant"), "llama-3.2-70b", "mixtral-8x7b-32768", "gemma2-9b-it"]
def _install():
    try:
        gh = __import__("satpambot.ml.groq_helper", fromlist=["*"])
    except Exception as e:
        log.debug("[groq_fallback] groq_helper import failed: %s", e); return
    base = getattr(gh, "chat", None)
    if not callable(base): return
    async def chat_wrap(*args, **kwargs):
        import asyncio
        last = None
        for m in _candidates():
            kwargs["model"] = m
            try: return await base(*args, **kwargs)
            except Exception as e:
                s = str(e).lower(); last = e
                if any(t in s for t in ("403","permission","blocked","not allowed")):
                    log.warning("[groq_fallback] model %s blocked; trying next", m); await asyncio.sleep(0.1); continue
                raise
        if last: raise last
    setattr(gh, "chat", chat_wrap); log.info("[groq_fallback] installed")
_install()

# ---- auto-added by patch: async setup stub for overlay ----
async def setup(bot):
    return