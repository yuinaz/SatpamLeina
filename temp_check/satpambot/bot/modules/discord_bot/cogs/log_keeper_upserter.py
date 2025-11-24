# -*- coding: utf-8 -*-
"""log_keeper_upserter.py
Memastikan pesan penting di #log-botphising tidak hilang & selalu pinned:
- Marker default: SATPAMBOT_PHASH_DB_V1, SATPAMBOT_STATUS_V1
- Jika ada banyak, pin yang terbaru dan unpin yang lama (opsional).
"""
from __future__ import annotations

from discord.ext import commands

import os, asyncio, logging, contextlib
import discord
from discord.ext import tasks

log = logging.getLogger(__name__)

LOG_PROTECT_MARKERS = [s.strip() for s in (os.getenv("LOG_PROTECT_MARKERS") or "SATPAMBOT_PHASH_DB_V1,SATPAMBOT_STATUS_V1").split(",") if s.strip()]
LOG_CH_ID = int(os.getenv("LOG_CHANNEL_ID") or 0)

class LogKeeperUpserter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task = None

    async def cog_load(self):
        if not LOG_CH_ID:
            log.info("[log_keeper_upserter] disabled (no LOG_CHANNEL_ID)")
            return
        self._task = self.ensure.start()

    def cog_unload(self):
        if self._task:
            self._task.cancel()

    def _has_marker(self, m: discord.Message) -> str | None:
        try:
            content = (m.content or "")
            for mk in LOG_PROTECT_MARKERS:
                if mk and mk in content:
                    return mk
            for e in (m.embeds or []):
                ttl = (getattr(e, "title", "") or "")
                ftxt = (getattr(getattr(e, "footer", None), "text", "") or "")
                for mk in LOG_PROTECT_MARKERS:
                    if mk in ttl or mk in ftxt:
                        return mk
        except Exception:
            pass
        return None

    @tasks.loop(count=1)
    async def ensure(self):
        await self.bot.wait_until_ready()
        ch = self.bot.get_channel(LOG_CH_ID)
        if not isinstance(ch, (discord.TextChannel, discord.Thread)):
            log.warning("[log_keeper_upserter] LOG_CHANNEL_ID not a text channel/thread")
            return

        # mapping marker -> latest message
        latest: dict[str, discord.Message] = {}
        async for m in ch.history(limit=200):
            mk = self._has_marker(m)
            if not mk:
                continue
            cur = latest.get(mk)
            if (not cur) or (m.created_at and cur.created_at and m.created_at > cur.created_at):
                latest[mk] = m

        for mk, msg in latest.items():
            try:
                if not msg.pinned:
                    with contextlib.suppress(Exception):
                        await msg.pin(reason=f"keeper {mk}")
                    log.info("[log_keeper_upserter] pinned %s", mk)
            except Exception:
                pass
async def setup(bot: commands.Bot):
    await bot.add_cog(LogKeeperUpserter(bot))