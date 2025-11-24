
from discord.ext import commands
import asyncio

class ProgressForceRefreshOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        loop = getattr(bot, "loop", None)
        if loop and hasattr(loop, "create_task"):
            self._task = loop.create_task(self._kick())
        else:
            # Smoke/DummyBot - skip scheduled task
            self._task = None

    async def _kick(self):
        # small periodic no-op to nudge progress reporters (runtime only)
        try:
            while True:
                await asyncio.sleep(1800)  # 30 min
        except asyncio.CancelledError:
            return
async def setup(bot):
    await bot.add_cog(ProgressForceRefreshOverlay(bot))