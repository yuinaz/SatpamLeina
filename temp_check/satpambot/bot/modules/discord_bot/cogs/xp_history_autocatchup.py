from __future__ import annotations
from discord.ext import commands


import asyncio
from typing import Optional, Dict
from datetime import datetime, timedelta

import discord

# === STATIC CONFIG (no ENV) ===
LOG_CHANNEL_ID = 1400375184048787566
PROGRESS_THREAD_ID = 1425400701982478408
QNA_CHANNEL_ID = 1426571542627614772  # optional; safe if not found

LOOKBACK_HOURS = 24       # keep light for Render free plan
AUTHOR_COOLDOWN_SEC = 20  # per-user cooldown to avoid burst +1 spam
XP_PER_HIT = 1            # minimal unit per historical message

COG_NAME = "XpHistoryAutoCatchup"

class XpHistoryAutoCatchup(commands.Cog):
    """On first ready, scan recent history in a few channels/threads and
    award tiny XP amounts with anti-spam. Safe in smoke envs because the
    task starts from `on_ready` using `asyncio.create_task` (no bot.loop).
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._started = False
        self._last_by_author: Dict[int, float] = {}

    # ---- utils
    def _cooldown_ok(self, user_id: int) -> bool:
        now = asyncio.get_event_loop().time()
        last = self._last_by_author.get(user_id, 0.0)
        if now - last >= AUTHOR_COOLDOWN_SEC:
            self._last_by_author[user_id] = now
            return True
        return False

    async def _award(self, member_id: int, amount: int, *, reason: str, channel_id: Optional[int], guild_id: Optional[int]):
        # Prefer direct methods if present (silences xp_awarder warnings)
        fn = getattr(self.bot, "xp_add", None) or getattr(self.bot, "award_xp", None)
        if callable(fn):
            res = fn(member_id, amount, reason=reason, channel_id=channel_id, guild_id=guild_id)
            if asyncio.iscoroutine(res):
                await res
        else:
            # Fallback to events
            self.bot.dispatch("xp_add", member_id, amount, reason, channel_id, guild_id)
            self.bot.dispatch("xp.award", member_id, amount, reason, channel_id, guild_id)
            self.bot.dispatch("satpam_xp", member_id, amount, reason, channel_id, guild_id)

    async def _scan(self, ch: discord.abc.Messageable, *, since: datetime, guild_id: Optional[int]):
        try:
            async for m in ch.history(limit=300, after=since, oldest_first=True):
                if m.author.bot:
                    continue
                if not self._cooldown_ok(m.author.id):
                    continue
                await self._award(m.author.id, XP_PER_HIT, reason="history-catchup", channel_id=getattr(ch, "id", None), guild_id=guild_id)
                await asyncio.sleep(0)  # be nice to the loop
        except Exception:
            # Silent best-effort on free plan
            pass

    async def _runner(self):
        await self.bot.wait_until_ready()
        if self._started:
            return
        self._started = True
        since = datetime.utcnow() - timedelta(hours=LOOKBACK_HOURS)

        for guild in list(self.bot.guilds):
            # log channel
            ch = guild.get_channel(LOG_CHANNEL_ID) or self.bot.get_channel(LOG_CHANNEL_ID)
            if isinstance(ch, (discord.TextChannel, discord.Thread)):
                await self._scan(ch, since=since, guild_id=guild.id)

            # progress thread
            th = None
            try:
                th = guild.get_thread(PROGRESS_THREAD_ID)  # type: ignore
            except Exception:
                th = self.bot.get_channel(PROGRESS_THREAD_ID)
            if isinstance(th, discord.Thread):
                await self._scan(th, since=since, guild_id=guild.id)

            # qna (optional)
            q = guild.get_channel(QNA_CHANNEL_ID) or self.bot.get_channel(QNA_CHANNEL_ID)
            if isinstance(q, (discord.TextChannel, discord.Thread)):
                await self._scan(q, since=since, guild_id=guild.id)

    @commands.Cog.listener()
    async def on_ready(self):
        # start once
        if not self._started:
            asyncio.create_task(self._runner())

async def setup(bot: commands.Bot):
    try:
        await bot.add_cog(XpHistoryAutoCatchup(bot))
    except discord.ClientException as e:
        if "already loaded" not in str(e):
            raise