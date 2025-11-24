from __future__ import annotations

from discord.ext import commands

import logging
log = logging.getLogger(__name__)
MODULES = [
    "satpambot.bot.modules.discord_bot.cogs.a12_weekly_random_xp",
]
class SatpamAutoloadWeekly(commands.Cog):
    def __init__(self, bot): self.bot = bot
    async def cog_load(self):
        for m in MODULES:
            try:
                await self.bot.load_extension(m); log.info("[autoload_weekly] loaded %s", m)
            except Exception as e:
                log.warning("[autoload_weekly] %s", e)
async def setup(bot): await bot.add_cog(SatpamAutoloadWeekly(bot))