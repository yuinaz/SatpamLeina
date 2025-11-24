from __future__ import annotations

from discord.ext import commands

import importlib, logging
log = logging.getLogger(__name__)

MODULES = ["satpambot.bot.modules.discord_bot.cogs.a26_memory_upsert_callsites_overlay"]

class UpsertAutoload(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    async def cog_load(self):
        for m in MODULES:
            try:
                importlib.import_module(m)
                log.info("[upsert_autoload] imported %s", m)
            except Exception as e:
                log.warning("[upsert_autoload] %s: %s", m, e)
async def setup(bot: commands.Bot):
    await bot.add_cog(UpsertAutoload(bot))