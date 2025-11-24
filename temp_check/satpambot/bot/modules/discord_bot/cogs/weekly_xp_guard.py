from __future__ import annotations
from discord.ext import commands

import asyncio, os, re, logging
from datetime import datetime, timezone
from typing import Optional, List
import discord

LOG = logging.getLogger("satpambot.bot.modules.discord_bot.cogs.weekly_xp_guard")
TITLE_PREFIX = os.getenv("WEEKLY_XP_TITLE_PREFIX","Weekly Random XP")
ANNOUNCE_CHANNEL_ID = int(os.getenv("WEEKLY_XP_ANNOUNCE_CHANNEL_ID","0"))
WEEK_RE = re.compile(r"(20\d{2}-W\d{2})")
def current_week_id()->str:
    now=datetime.now(timezone.utc); y,w,_=now.isocalendar(); return f"{y}-W{int(w):02d}"
def _extract_week_from_embed(e: discord.Embed) -> str|None:
    for text in filter(None,[e.title, e.description] + [f.value for f in e.fields]):
        m=WEEK_RE.search(str(text)); 
        if m: return m.group(1)
    return None

class WeeklyXPGuard(commands.Cog):
    def __init__(self, bot): self.bot=bot; self._task=None
    @commands.Cog.listener()
    async def on_ready(self):
        if self._task: return
        self._task=asyncio.create_task(self._run())
    async def _run(self):
        await asyncio.sleep(int(os.getenv("WEEKLY_XP_GUARD_DELAY","20")))
        if not ANNOUNCE_CHANNEL_ID: return
        ch = self.bot.get_channel(ANNOUNCE_CHANNEL_ID) or await self.bot.fetch_channel(ANNOUNCE_CHANNEL_ID)
        cw=current_week_id()
        msgs: List[discord.Message]=[]
        async for m in ch.history(limit=200, oldest_first=False):
            if m.author.id!=self.bot.user.id or not m.embeds: continue
            e=m.embeds[0]
            if not (e.title or "").startswith(TITLE_PREFIX): continue
            w=_extract_week_from_embed(e) or cw
            if w==cw: msgs.append(m)
        if len(msgs)<=1: return
        for m in msgs[1:]:
            try: await m.delete(); await asyncio.sleep(0.2)
            except Exception: pass

async def setup(bot):
    res = await bot.add_cog(WeeklyXPGuard(bot))
    import asyncio as _aio
    if _aio.iscoroutine(res): await res