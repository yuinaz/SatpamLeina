from __future__ import annotations

from discord.ext import commands

import discord, json, asyncio, os, time
from pathlib import Path
from discord.ext import tasks
import logging

log = logging.getLogger(__name__)

class PresenceWatcher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.path = Path("data/presence_override.json")
        self.last_mtime = 0.0
        self.loop.start()

    def cog_unload(self):
        try: self.loop.cancel()
        except: pass

    @tasks.loop(seconds=7.0)
    async def loop(self):
        try:
            if not self.path.exists():
                return
            st = self.path.stat().st_mtime
            if st <= self.last_mtime:
                return
            self.last_mtime = st
            data = json.loads(self.path.read_text("utf-8"))
            mode = str(data.get("mode","auto")).lower()
            if mode != "manual":
                return
            tp = str(data.get("type","playing")).lower()
            txt = str(data.get("text",""))
            status = str(data.get("status","online")).lower()
            url = str(data.get("url","")).strip() or None

            # map types
            tmap = {
                "playing": discord.ActivityType.playing,
                "listening": discord.ActivityType.listening,
                "watching": discord.ActivityType.watching,
                "competing": discord.ActivityType.competing,
                "streaming": discord.ActivityType.streaming,
            }
            smap = {
                "online": discord.Status.online,
                "idle": discord.Status.idle,
                "dnd": discord.Status.dnd,
                "invisible": discord.Status.invisible,
            }
            atype = tmap.get(tp, discord.ActivityType.playing)
            dstatus = smap.get(status, discord.Status.online)

            activity = None
            if atype is discord.ActivityType.streaming and url:
                activity = discord.Streaming(name=txt or "Streaming", url=url)
            else:
                activity = discord.Activity(type=atype, name=txt or "/help")

            await self.bot.change_presence(activity=activity, status=dstatus)
            log.info("[presence] applied manual presence: %s %s (%s)", tp, txt, status)
        except Exception as e:
            log.warning("[presence] watcher error: %s", e)

    @loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
async def setup(bot: commands.Bot):
    await bot.add_cog(PresenceWatcher(bot))