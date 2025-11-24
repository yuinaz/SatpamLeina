from __future__ import annotations

from discord.ext import commands

import importlib, logging
log = logging.getLogger(__name__)
MODULES = [
    "satpambot.bot.modules.discord_bot.cogs.a05_autodelete_exempt_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a06_logger_noise_filter_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a06_selfheal_import_guard_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a06_alert_coalescer_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a07_periodic_status_throttle_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a06_groq_model_fallback_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a06_selfheal_json_guard_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a08_public_clearchat",
    "satpambot.bot.modules.discord_bot.cogs.a11_bonus_xp_once",
]
class SatpamUnifiedAutoload(commands.Cog):
    def __init__(self, bot): self.bot = bot
    async def cog_load(self):
        for m in MODULES:
            try:
                await self.bot.load_extension(m); log.info("[autoload_unified] loaded %s", m)
            except Exception as e:
                try:
                    importlib.import_module(m); log.info("[autoload_unified] imported %s", m)
                except Exception as e2:
                    log.warning("[autoload_unified] %s: %s / %s", m, e, e2)
async def setup(bot): await bot.add_cog(SatpamUnifiedAutoload(bot))