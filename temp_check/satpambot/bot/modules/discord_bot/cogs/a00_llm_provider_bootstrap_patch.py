from __future__ import annotations

"""
LLM provider bootstrap patch:
- Guarantees bot.llm_ask is available.
- Picks sane defaults for model IDs via env or constants.
"""

import os, logging

log = logging.getLogger(__name__)

DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL_ID", "llama-3.1-8b-instant")
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL_ID", "gemini-2.5-flash-lite")
async def setup(bot):
    # Prefer native provider 'ask' if present
    try:
        from satpambot.bot.llm_providers import ask as native_ask  # type: ignore
        bot.llm_ask = native_ask
        log.info("[llm-bootstrap] using native satpambot.bot.llm_providers.ask")
        return
    except Exception as e:
        log.warning("[llm-bootstrap] native ask missing: %r; using facade", e)

    # Fallback to providers facade overlay
    try:
        from satpambot.bot.modules.discord_bot.cogs.a06_providers_facade_overlay import LLM
    except Exception as e:
        log.error("[llm-bootstrap] providers facade missing: %r", e)
        return

    async def llm_ask(prompt: str, *, prefer="auto", **kw):
        # prefer: auto|groq|gemini
        prefer = (prefer or "auto").lower()
        if prefer == "groq":
            return await LLM.ask(prompt, provider="groq", model=os.getenv("GROQ_MODEL_ID", DEFAULT_GROQ_MODEL), **kw)
        if prefer == "gemini":
            return await LLM.ask(prompt, provider="gemini", model=os.getenv("GEMINI_MODEL_ID", DEFAULT_GEMINI_MODEL), **kw)
        # auto: try groq then gemini
        try:
            return await LLM.ask(prompt, provider="groq", model=os.getenv("GROQ_MODEL_ID", DEFAULT_GROQ_MODEL), **kw)
        except Exception as e:
            log.warning("[llm-bootstrap] groq failed, fallback gemini: %r", e)
            return await LLM.ask(prompt, provider="gemini", model=os.getenv("GEMINI_MODEL_ID", DEFAULT_GEMINI_MODEL), **kw)

    bot.llm_ask = llm_ask
    log.info("[llm-bootstrap] bot.llm_ask installed (facade)")