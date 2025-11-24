
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

class SelfhealQuorumV2Overlay(commands.Cog):
    def __init__(self, bot: Any):
        self.bot = bot
        log.info("a00_selfheal_quorum_v2_overlay loaded (stub active)")
async def setup(bot):
    await bot.add_cog(SelfhealQuorumV2Overlay(bot))
def setup_old(bot):
    bot.add_cog(SelfhealQuorumV2Overlay(bot))
