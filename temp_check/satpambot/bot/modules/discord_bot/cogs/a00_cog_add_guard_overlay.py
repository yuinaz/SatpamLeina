
# a00_cog_add_guard_overlay.py (v7.5)
# Wrap bot.add_cog to skip duplicates by cog name to avoid "already loaded" warnings.
from discord.ext import commands
import logging, asyncio, inspect

log = logging.getLogger(__name__)

class CogAddGuard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._patch_add_cog()

    def _patch_add_cog(self):
        bot = self.bot
        orig = getattr(bot, "add_cog")
        if getattr(bot, "_add_cog_guard_patched", False):
            return
        async def add_cog_guard(cog, *args, **kwargs):
            name = getattr(cog, "qualified_name", getattr(cog, "__cog_name__", cog.__class__.__name__))
            if name in getattr(bot, "cogs", {}):
                log.info("[cog-guard] skip duplicate cog: %s", name)
                return
            res = orig(cog, *args, **kwargs)
            if inspect.isawaitable(res):
                return await res
            return res
        bot.add_cog = add_cog_guard
        bot._add_cog_guard_patched = True
        log.info("[cog-guard] add_cog patched")
async def setup(bot):
    try:
        await bot.add_cog(CogAddGuard(bot))
    except Exception as e:
        log.info("[cog-guard] setup swallowed: %r", e)