
from discord.ext import commands
"""
Ensure delete_safe_shim_plus.summary logger does not duplicate messages.
Forces propagate=False so summaries appear only once.
"""
import logging

class LogSummarySingleton(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        for name in ("satpambot.bot.modules.discord_bot.cogs.delete_safe_shim_plus.summary",
                     "modules.discord_bot.cogs.delete_safe_shim_plus.summary"):
            logger = logging.getLogger(name)
            logger.propagate = False
            # Set level to INFO (or keep if stricter) without adding extra handlers
            if logger.level == logging.NOTSET:
                logger.setLevel(logging.INFO)
async def setup(bot):
    await bot.add_cog(LogSummarySingleton(bot))