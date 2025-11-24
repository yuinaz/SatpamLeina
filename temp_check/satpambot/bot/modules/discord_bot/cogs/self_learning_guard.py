
from discord.ext import commands
class SelfLearningGuard(commands.Cog):
    """Defensive no-op guard for smoke environment."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
async def setup(bot: commands.Bot):
    await bot.add_cog(SelfLearningGuard(bot))