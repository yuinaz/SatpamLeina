
from discord.ext import commands
import logging

log = logging.getLogger(__name__)
class AutoLearnConfigListener(commands.Cog):
    def __init__(self, bot): self.bot = bot
async def setup(bot): await bot.add_cog(AutoLearnConfigListener(bot))
def setup(bot): 
    try:
        import asyncio
        if asyncio.get_event_loop().is_running():
            return asyncio.create_task(bot.add_cog(AutoLearnConfigListener(bot)))
    except Exception: pass
    return bot.add_cog(AutoLearnConfigListener(bot))