from __future__ import annotations
from discord.ext import commands


import logging
log = logging.getLogger(__name__)
MODULES = [
    "satpambot.bot.modules.discord_bot.cogs.a02_miner_jitter_overlay",
    "satpambot.bot.modules.discord_bot.cogs.xp_command",
    "satpambot.bot.modules.discord_bot.cogs.web_search_fallback",
    "satpambot.bot.modules.discord_bot.cogs.a02_intents_probe_quiet_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a12_weekly_random_xp",
]
class AutoloadXpJitterWeb(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    async def cog_load(self):
        for m in MODULES:
            try:
                await self.bot.load_extension(m)
                log.info("[autoload_xp_jitter_web] loaded %s", m)
            except Exception as e:
                log.warning("[autoload_xp_jitter_web] %s", e)
async def setup(bot):
    await bot.add_cog(AutoloadXpJitterWeb(bot))