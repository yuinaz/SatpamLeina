
import asyncio, logging, os
from discord.ext import commands
log = logging.getLogger(__name__)

class FixQnAAutolearnInterval(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._t = asyncio.create_task(self._patch())

    async def _patch(self):
        await self.bot.wait_until_ready()
        default_sec = int(os.getenv("QNA_SEED_INTERVAL_SEC", "180"))
        n = 0
        for name, cog in list(self.bot.cogs.items()):
            try:
                looks_like = type(cog).__name__ in {"QnAAutoLearnScheduler","QnAAutolearnScheduler"} or hasattr(cog, "send_seed_embed")
                if looks_like and not hasattr(cog, "interval_sec"):
                    setattr(cog, "interval_sec", default_sec)
                    log.warning("[qna_autolearn_fix] set %s.interval_sec=%s", name, default_sec)
                    n += 1
            except Exception as e:
                log.exception("[qna_autolearn_fix] error %s: %r", name, e)
        if not n:
            log.info("[qna_autolearn_fix] nothing to patch")

    async def cog_unload(self):
        try: self._t.cancel()
        except Exception: pass

def _inject(bot):
    flag = "_fix_qna_autolearn_interval_overlay_loaded"
    if getattr(bot, flag, False): return
    setattr(bot, flag, True)
    bot.add_cog(FixQnAAutolearnInterval(bot))

def setup(bot): _inject(bot)
async def setup(bot): _inject(bot)
