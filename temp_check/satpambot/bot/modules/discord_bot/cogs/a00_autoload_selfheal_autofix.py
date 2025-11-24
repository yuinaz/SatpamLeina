from __future__ import annotations

from discord.ext import commands

import logging
log = logging.getLogger(__name__)
MODULES = ["satpambot.bot.modules.discord_bot.cogs.selfheal_autofix",
           "satpambot.bot.modules.discord_bot.cogs.a06_selfheal_json_guard_overlay",
           "satpambot.bot.modules.discord_bot.cogs.a06_groq_model_fallback_overlay"]
class AutoloadSelfhealAutofix(commands.Cog):
    def __init__(self, bot): self.bot = bot
    async def cog_load(self):
        for m in MODULES:
            try:
                await self.bot.load_extension(m); log.info("[autoload_selfheal_autofix] loaded %s", m)
            except Exception as e:
                log.warning("[autoload_selfheal_autofix] %s", e)
async def setup(bot): await bot.add_cog(AutoloadSelfhealAutofix(bot))