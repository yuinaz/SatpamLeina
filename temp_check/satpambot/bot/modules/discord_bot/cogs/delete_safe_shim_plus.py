# -*- coding: utf-8 -*-
"""delete_safe_shim_plus.py (v3)
Proteksi kuat:
- pinned
- keeper neuro ("presence::keeper", "neuro-memory::keeper")
- pesan log lama (pre-session)
- pesan log dengan marker khusus (judul/teks/EMBED title/footer): LOG_PROTECT_MARKERS
"""
from __future__ import annotations

from discord.ext import commands

import os, logging, contextlib, time
from typing import Optional, Iterable
import discord

log = logging.getLogger(__name__)

STARTUP_TS = 1760011101
DEFAULT_NEURO_THREAD = os.getenv("NEURO_THREAD_NAME", "neuro-lite progress").strip().lower()

def _int_env(name: str) -> Optional[int]:
    v = (os.getenv(name) or "").strip()
    try:
        return int(v) if v else None
    except Exception:
        return None

LOG_CH_ID = _int_env("LOG_CHANNEL_ID")
LOG_PROTECT_MARKERS: Iterable[str] = tuple([s.strip() for s in (os.getenv("LOG_PROTECT_MARKERS") or "SATPAMBOT_PHASH_DB_V1,SATPAMBOT_STATUS_V1").split(",") if s.strip()])

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
                if not m:
                    continue
                if m in ttl or m in ftxt:
                    return True
    except Exception:
        pass
    return False

def setup_delete_guard():
    orig_delete = discord.Message.delete

    async def _safe_delete(self: discord.Message, *a, **kw):
        try:
            # 0) Always protect pinned
            if getattr(self, "pinned", False):
                log.info("[delete_safe_plus] ignore delete for pinned in #%s",
                         getattr(getattr(self, "channel", None), "name", "?"))
                return

            ch = getattr(self, "channel", None)
            ch_name = (getattr(ch, "name", "") or "").strip().lower()

            # 1) Protect presence/neuro keeper in neuro thread
            if isinstance(ch, discord.Thread) and ch_name == DEFAULT_NEURO_THREAD:
                text = (getattr(self, "content", "") or "")
                if ("neuro-memory::keeper" in text) or ("presence::keeper" in text):
                    log.info("[delete_safe_plus] ignore delete for keeper in #neuro thread")
                    return

            # 2) Session-scope protection for log channel (pre-session messages)
            if LOG_CH_ID and isinstance(getattr(ch, "id", None), int) and ch.id == LOG_CH_ID:
                if _has_marker(self):
                    log.info("[delete_safe_plus] ignore delete for protected marker message in log")
                    return
                created_ts = int(self.created_at.timestamp()) if getattr(self, "created_at", None) else None
                if created_ts and created_ts < STARTUP_TS:
                    log.info("[delete_safe_plus] ignore delete for pre-session log message (session-scope)")
                    return
        except Exception:
            pass
        return await orig_delete(self, *a, **kw)

    discord.Message.delete = _safe_delete
    log.info("[delete_safe_plus] Message.delete patched (pinned+keeper+session log protect+markers)")

class DeleteSafeShimPlus(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        setup_delete_guard()
async def setup(bot: commands.Bot):
    await bot.add_cog(DeleteSafeShimPlus(bot))