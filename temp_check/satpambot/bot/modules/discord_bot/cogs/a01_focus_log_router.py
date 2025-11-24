
from discord.ext import commands
class FocusLogRouter(commands.Cog):
    """Minimal focus/log router for smoke tests.
    In production, another overlay (a99_focus_log_router_final) provides the heavy lifting.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
async def setup(bot: commands.Bot):
    await bot.add_cog(FocusLogRouter(bot))