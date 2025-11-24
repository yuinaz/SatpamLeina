
# a00_logging_quiet_preset_overlay.py
from discord.ext import commands
import logging

TARGETS = {
    # demote noisy-but-harmless duplicates
    "satpambot.bot.modules.discord_bot.cogs.a00_overlay_autoload_plus": logging.INFO,
    "satpambot.bot.modules.discord_bot.cogs.a00_overlay_autoload_weekly": logging.INFO,
    # dm muzzle and neuro bootstrap are informative, not problematic
    "satpambot.bot.modules.discord_bot.cogs.dm_muzzle": logging.INFO,
    "satpambot.bot.modules.discord_bot.cogs.neuro_governor_bootstrap": logging.INFO,
    # llm bootstrap warns when falling back; treat as info
    "satpambot.bot.modules.discord_bot.cogs.a00_llm_provider_bootstrap": logging.INFO,
}

class LoggingQuietPreset(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        for name, lvl in TARGETS.items():
            logging.getLogger(name).setLevel(lvl)
async def setup(bot):
    await bot.add_cog(LoggingQuietPreset(bot))