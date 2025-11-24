# -*- coding: utf-8 -*-
"""log_autodelete_scoped.py (v3)
Auto-delete pesan di channel log HANYA dari sesi saat ini (session-scope).
- Hanya hapus pesan buatan bot sendiri (author == me)
- Tidak menyentuh pinned
- Tidak menyentuh keeper markers ("presence::keeper", "neuro-memory::keeper")
- Tidak menyentuh pesan yang berisi LOG_PROTECT_MARKERS (di content / embed title/footer)
- TTL dikontrol ENV LOG_AUTODELETE_TTL (default 900 detik)
- Scan periodik ENV LOG_AUTODELETE_SCAN_EVERY (default 30 detik)
- Channel = LOG_CHANNEL_ID (wajib)
"""
from __future__ import annotations

from discord.ext import commands

import os, asyncio, logging, time, contextlib
import discord
from discord.ext import tasks

log = logging.getLogger(__name__)

def _env_int(name: str, d: int) -> int:
    try:
        v = int((os.getenv(name) or "").strip())
        return v if v > 0 else d
    except Exception:
        return d

def _env_bool(name: str, default: bool=False) -> bool:
    v = (os.getenv(name) or "").strip().lower()
    if not v:
        return default
    return v not in ("0","false","no")

STARTUP_TS = int(time.time())
TTL = _env_int("LOG_AUTODELETE_TTL", 900)
SCAN_EVERY = _env_int("LOG_AUTODELETE_SCAN_EVERY", 30)
ENABLED = _env_bool("LOG_AUTODELETE_ENABLE", True)
LOG_PROTECT_MARKERS = [s.strip() for s in (os.getenv("LOG_PROTECT_MARKERS") or "SATPAMBOT_PHASH_DB_V1,SATPAMBOT_STATUS_V1").split(",") if s.strip()]

def _int_env(name: str):
    v = (os.getenv(name) or "").strip()
    try:
        return int(v) if v else None
    except Exception:
        return None

LOG_CH_ID = _int_env("LOG_CHANNEL_ID")

def _has_marker(msg: discord.Message) -> bool:
    try:
        content = (getattr(msg, "content", "") or "")
        for m in LOG_PROTECT_MARKERS:
            if m and m in content:
                return True
        for e in (msg.embeds or []):
            ttl = (getattr(e, "title", "") or "")
            ftxt = (getattr(getattr(e, "footer", None), "text", "") or "")
            for m in LOG_PROTECT_MARKERS:
                if m in ttl or m in ftxt:
                    return True
    except Exception:
        pass
    return False

class LogAutoDeleteScoped(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task = None

    async def cog_load(self):
        if not ENABLED or not LOG_CH_ID:
            log.info("[log_autodelete_scoped] disabled (ENABLED=%s, LOG_CHANNEL_ID=%s)", ENABLED, LOG_CH_ID)
            return
        self._task = self.loop_scan.start()

    def cog_unload(self):
        if self._task:
            self._task.cancel()

    @tasks.loop(seconds=SCAN_EVERY)
    async def loop_scan(self):
        await self.bot.wait_until_ready()
        ch = self.bot.get_channel(LOG_CH_ID)
        if not isinstance(ch, (discord.TextChannel, discord.Thread)):
            return
        try:
            me = ch.guild.me if isinstance(ch, discord.TextChannel) else getattr(ch, "me", None)
        except Exception:
            me = None
        cutoff = time.time() - TTL
        async for m in ch.history(limit=200):
            try:
                if getattr(m, "pinned", False):
                    continue
                if me and m.author.id != me.id:
                    continue
                if _has_marker(m):
                    continue
                if ("presence::keeper" in (m.content or "")) or ("neuro-memory::keeper" in (m.content or "")):
                    continue
                created_ts = int(m.created_at.timestamp()) if m.created_at else 0
                # Session-only delete: hanya hapus pesan yang lahir SETELAH bot online
                if created_ts < STARTUP_TS:
                    continue
                if created_ts <= cutoff:
                    with contextlib.suppress(Exception):
                        await m.delete()
            except Exception:
                pass
        log.debug("[log_autodelete_scoped] scanned channel %s", getattr(ch, "name", LOG_CH_ID))
async def setup(bot: commands.Bot):
    await bot.add_cog(LogAutoDeleteScoped(bot))