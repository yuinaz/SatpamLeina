
from __future__ import annotations
import os, asyncio, logging
from typing import Tuple, Optional, List
from discord.ext import commands

log = logging.getLogger(__name__)

def _order() -> List[str]:
    raw = os.getenv("QNA_PROVIDER_ORDER", "gemini,groq") or "gemini,groq"
    return [s.strip().lower() for s in raw.split(",") if s.strip()]

def _model_for(provider: str) -> str:
    if provider.startswith("gem"):
        return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    return os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

async def _ask_llm(provider: str, prompt: str) -> Optional[str]:
    try:
        from satpambot.bot.providers.llm_facade import ask  # type: ignore
    except Exception as e:
        log.warning("[qna-dual] llm_facade missing: %r", e)
        return None
    try:
        text = await ask(provider=provider, model=_model_for(provider),
                         messages=[{"role":"user","content":prompt}], system="Jawab ringkas dan aman.")
        return (text or "").strip() or None
    except Exception as e:
        log.warning("[qna-dual] provider %s failed: %r", provider, e)
        return None

class QnaDualProvider(commands.Cog):
    """Tiny facade to answer a question using provider order env."""
    def __init__(self, bot: commands.Bot | None = None):
        self.bot = bot

    async def aask(self, prompt: str) -> Tuple[str, str]:
        for prov in _order() or ["gemini","groq"]:
            ans = await _ask_llm(prov, prompt)
            if ans:
                return ans, ("Gemini" if prov.startswith("gem") else "Groq")
        return "Provider QnA belum terkonfigurasi.", ""

    # Sync helper (not used by runtime, but for backward compat)
    def ask(self, prompt: str) -> Tuple[str, str]:
        return asyncio.get_event_loop().run_until_complete(self.aask(prompt))

async def setup(bot: commands.Bot):
    await bot.add_cog(QnaDualProvider(bot))
