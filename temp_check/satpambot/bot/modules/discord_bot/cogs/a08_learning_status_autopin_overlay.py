from discord.ext import commands
import os, json, logging
from datetime import datetime, timezone

from discord.ext import commands, tasks

from ..helpers.compat_learning_status import read_learning_status

log = logging.getLogger(__name__)

class LearningStatusAutopin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.period = max(60, int(os.getenv("LEARNING_AUTOPIN_PERIOD_SEC","300") or "300"))
        try:
            self.channel_id = int(os.getenv("LEARNING_STATUS_CHANNEL_ID","") or "0") or None
        except Exception:
            self.channel_id = None
        if self.channel_id:
            self.task = self.loop.start()

    def cog_unload(self):
        try: self.loop.cancel()
        except Exception: pass

    @tasks.loop(seconds=30)
    async def loop(self):
        try:
            from discord import Game, Status
            import aiohttp

            now = datetime.now(timezone.utc)
            if int(now.timestamp()) % self.period != 0:
                return
            if not self.channel_id:
                return
            ch = self.bot.get_channel(self.channel_id) or await self.bot.fetch_channel(self.channel_id)
            if not ch: return
            base = os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/")
            token = os.getenv("UPSTASH_REDIS_REST_TOKEN","")
            if not (base and token): return
            async with aiohttp.ClientSession() as session:
                s = await read_learning_status(session, base, token)
            txt = f"📚 {s['label']} • {s['percent']:.1f}% (rem {s['remaining']})"
            await ch.send(txt)
        except Exception as e:
            log.warning("[learn-status] refresh failed: %r", e)

    @loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
async def setup(bot):
    await bot.add_cog(LearningStatusAutopin(bot))