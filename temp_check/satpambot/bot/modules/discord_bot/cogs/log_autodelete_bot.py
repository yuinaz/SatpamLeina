
from discord.ext import commands
import asyncio, datetime as dt
import discord
from discord.ext import tasks
from discord.errors import Forbidden
from satpambot.config.compat_conf import get as cfg

ENABLED = bool(cfg("LOG_AUTODELETE_ENABLED", True, bool))

class LogAutoDeleteBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if ENABLED:
            self._task.start()

    def cog_unload(self):
        try: self._task.cancel()
        except Exception: pass

    @tasks.loop(minutes=15)
    async def _task(self):
        try:
            for g in self.bot.guilds:
                for ch in g.text_channels:
                    try:
                        async for m in ch.history(limit=200, oldest_first=False):
                            if m.author.id == self.bot.user.id and m.embeds and (dt.datetime.utcnow()-m.created_at).total_seconds() > 86400:
                                try: await m.delete()
                                except Forbidden: pass
                                await asyncio.sleep(0.2)
                    except Forbidden:
                        continue
        except Exception:
            pass

    @_task.before_loop
    async def before(self):
        await self.bot.wait_until_ready()
async def setup(bot):
    await bot.add_cog(LogAutoDeleteBot(bot))