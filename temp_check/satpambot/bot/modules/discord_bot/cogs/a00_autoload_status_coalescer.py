from __future__ import annotations

from discord.ext import commands

import logging
log = logging.getLogger(__name__)
class AutoloadStatusCoalescer(commands.Cog):
    def __init__(self, bot): self.bot = bot
    async def cog_load(self):
        try:
            await self.bot.load_extension("satpambot.bot.modules.discord_bot.cogs.a06_status_coalescer_overlay")
        except Exception as e:
            log.warning("[autoload_status_coalescer] %s", e)
async def setup(bot): await bot.add_cog(AutoloadStatusCoalescer(bot))