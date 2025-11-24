
from discord.ext import commands
import logging

log = logging.getLogger(__name__)

class EmbedScribeUpdateAsyncFallback(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
async def setup(bot):
    await bot.add_cog(EmbedScribeUpdateAsyncFallback(bot))