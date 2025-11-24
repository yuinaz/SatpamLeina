from discord.ext import commands

import logging

log = logging.getLogger(__name__)

class XPStoreCompatOverlay(commands.Cog):
    """Minimal overlay to ensure XP store compatibility without noisy runtime warnings.
    This version only exists to be a safe, awaitable loader in discord.py 2.x."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    # discord.py 2.x style loader
    name = XPStoreCompatOverlay.__name__
    if getattr(bot, "cogs", None) and name in bot.cogs:
        log.info("[xp_store_compat_overlay] already loaded, skipping")
        return
    await bot.add_cog(XPStoreCompatOverlay(bot))
    log.info("[xp_store_compat_overlay] loaded OK")