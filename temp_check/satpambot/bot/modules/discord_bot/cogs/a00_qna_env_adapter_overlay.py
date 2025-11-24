
from __future__ import annotations
import os, logging
from discord.ext import commands

log = logging.getLogger(__name__)

class QnaEnvAdapterOverlay(commands.Cog):
    """
    Normalize env for Gemini/Groq providers:
    - If GEMINI_API_KEY exists and GOOGLE_API_KEY missing -> mirror to GOOGLE_API_KEY
    - Optionally enforce QNA_PROVIDER_ORDER leading with 'gemini' when Gemini key present
    """
    def __init__(self, bot):
        self.bot = bot
        gmk = os.getenv("GEMINI_API_KEY")
        ggl = os.getenv("GOOGLE_API_KEY")
        if gmk and not ggl:
            os.environ["GOOGLE_API_KEY"] = gmk
            log.info("[qna-env] mirrored GEMINI_API_KEY -> GOOGLE_API_KEY")
        # Provider order
        order = os.getenv("QNA_PROVIDER_ORDER", "")
        if gmk:
            if not order:
                os.environ["QNA_PROVIDER_ORDER"] = "gemini,groq"
                log.info("[qna-env] defaulted QNA_PROVIDER_ORDER=gemini,groq")
            elif order.split(",")[0].strip().lower() != "gemini":
                # keep user choice if explicitly set, but log a warning
                log.warning("[qna-env] GEMINI_API_KEY present but provider order is '%s'", order)

async def setup(bot):
    await bot.add_cog(QnaEnvAdapterOverlay(bot))
