from discord.ext import commands
import os, logging
import discord

logger = logging.getLogger(__name__)

class QnaGuardPatch(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # nothing heavy here; placeholder to keep compatibility
async def setup(bot: commands.Bot):
    await bot.add_cog(QnaGuardPatch(bot))