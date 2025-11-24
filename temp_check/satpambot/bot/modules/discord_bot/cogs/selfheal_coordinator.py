from discord.ext import commands
import os, logging
from datetime import datetime, timezone

from discord.ext import tasks

log = logging.getLogger(__name__)

class SelfhealCoordinator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.period = max(10, int(os.getenv("SELFHEAL_TICK_SEC","30") or "30"))
        self._tasks = []  # list of dicts {"status": "queued"|"done"}
        self.task = self._tick_process.start()

    def cog_unload(self):
        try: self._tick_process.cancel()
        except Exception: pass

    @tasks.loop(seconds=5)
    async def _tick_process(self):
        now = datetime.now(timezone.utc)
        if int(now.timestamp()) % self.period != 0:
            return
        # Safe iteration
        for i, t in enumerate(list(self._tasks)):
            if not isinstance(t, dict):
                continue
            if t.get("status") != "queued":
                continue
            # simulate process
            t["status"] = "done"

    @_tick_process.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
async def setup(bot):
    await bot.add_cog(SelfhealCoordinator(bot))