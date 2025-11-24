from __future__ import annotations

from discord.ext import commands
import logging

log = logging.getLogger(__name__)

NEURO_EXTS = [
    "satpambot.bot.modules.discord_bot.cogs.neuro_autolearn_moderated_v2",
    "satpambot.bot.modules.discord_bot.cogs.neuro_curriculum_bridge",
    "satpambot.bot.modules.discord_bot.cogs.neuro_shadow_bridge",
    "satpambot.bot.modules.discord_bot.cogs.neuro_progress_mapper",
    "satpambot.bot.modules.discord_bot.cogs.neuro_governor_levels",
]

class NeuroSuiteAutoload(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
async def setup(bot: commands.Bot):
    # silently try to load all; ignore "already loaded"
    for ext in NEURO_EXTS:
        try:
            await bot.load_extension(ext)
            log.info("[neuro-suite] loaded: %s", ext)
        except Exception as e:
            log.info("[neuro-suite] skip %s (%s)", ext, e.__class__.__name__)
    await bot.add_cog(NeuroSuiteAutoload(bot))