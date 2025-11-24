from __future__ import annotations

from discord.ext import commands

import os, asyncio, logging, signal, time
import discord
from discord.ext import tasks
from ..helpers import env_store

log = logging.getLogger(__name__)

class GracefulRuntime(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ready_ts = 0.0
        self._closed = False
        self.readybeat.start()
        try:
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(self._graceful_terminate("SIGTERM")))
            loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(self._graceful_terminate("SIGINT")))
        except Exception:
            pass

    def cog_unload(self):
        try: self.readybeat.cancel()
        except Exception: pass

    @tasks.loop(seconds=15.0)
    async def readybeat(self):
        try:
            env_store.set("RUNTIME_READY_TS", str(int(self._ready_ts or 0)), source="graceful")
            env_store.set("RUNTIME_ALIVE_TS", str(int(time.time())), source="graceful")
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        self._ready_ts = time.time()
        delay = int(env_store.get("READY_DELAY_SECS") or os.getenv("READY_DELAY_SECS") or "0")
        if delay > 0:
            await asyncio.sleep(delay)

    async def _graceful_terminate(self, why: str):
        if self._closed: return
        self._closed = True
        try:
            await asyncio.sleep(0.5)
            await self.bot.close()
        except Exception:
            pass
        finally:
            os._exit(0)

    @commands.command(name="selfrestart")
    async def cmd_selfrestart(self, ctx: commands.Context):
        await ctx.reply("Restarting gracefully…", mention_author=False)
        await self._graceful_terminate("owner-cmd")
async def setup(bot: commands.Bot):
    await bot.add_cog(GracefulRuntime(bot))