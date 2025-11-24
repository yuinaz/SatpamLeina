
import logging
from typing import Any
try:
    import discord
    from discord.ext import commands
except Exception:
    class commands:  # type: ignore
        class Cog: ...
        @staticmethod
        def command(*a, **kw):
            def deco(fn): return fn
            return deco
    class discord:  # type: ignore
        class Intents: ...
        class Message: ...
log = logging.getLogger(__name__)

class SmokeAutodetectOverlay(commands.Cog):
    def __init__(self, bot: Any):
        self.bot = bot
        log.info("a97_smoke_autodetect_overlay loaded (stub active)")
async def setup(bot):
    await bot.add_cog(SmokeAutodetectOverlay(bot))
def setup_old(bot):
    bot.add_cog(SmokeAutodetectOverlay(bot))
