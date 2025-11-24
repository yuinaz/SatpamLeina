from __future__ import annotations

import logging, os
from typing import Optional
import discord
from .errorlog_helper import log_error_embed

log = logging.getLogger(__name__)
TARGET_THREAD_NAME = "Ban Log"

def _to_int(val: str) -> int:
    try:
        return int((val or "").strip())
    except Exception:
        return 0

# -------------- Resolution helpers --------------
def _resolve_thread_host_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    """Return the channel where the Ban Log THREAD must live.
    STRICT: Only #log-botphising via LOG_CHANNEL_ID or LOG_CHANNEL_NAME ('log-botphising').
    """
    # 1) Explicit ID
    log_id = _to_int(os.getenv("LOG_CHANNEL_ID", ""))
    if log_id:
        ch = guild.get_channel(log_id)
        if isinstance(ch, discord.TextChannel):
            log.info("[banlog] host=ID  #%s (%s)", getattr(ch, "name","?"), getattr(ch,"id","?"))
            return ch

    # 2) Explicit NAME
    name = (os.getenv("LOG_CHANNEL_NAME","") or "").strip()
    if name:
        cand = discord.utils.get(guild.text_channels, name=name)
        if isinstance(cand, discord.TextChannel):
            log.info("[banlog] host=NAME #%s (%s)", getattr(cand, "name","?"), getattr(cand,"id","?"))
            return cand

    # 3) Hard default: exact 'log-botphising' only
    cand = discord.utils.get(guild.text_channels, name="log-botphising")
    if isinstance(cand, discord.TextChannel):
        log.info("[banlog] host=DEFAULT #%s (%s)", getattr(cand, "name","?"), getattr(cand,"id","?"))
        return cand

    log.warning("[banlog] host channel for thread NOT FOUND (expected #log-botphising).")
    return None

def _resolve_announce_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    """Return the public channel to announce a successful ban (e.g. #💬︲ngobrol).
    Priority: BAN_LOG_CHANNEL_ID > LOG_BAN_CHANNEL_ID > BAN_LOG_CHANNEL_NAME > '💬︲ngobrol'.
    """
    for key in ("BAN_LOG_CHANNEL_ID", "LOG_BAN_CHANNEL_ID"):
        cid = _to_int(os.getenv(key, ""))
        if cid:
            ch = guild.get_channel(cid)
            if isinstance(ch, discord.TextChannel):
                return ch
    nm = (os.getenv("BAN_LOG_CHANNEL_NAME","") or "").strip()
    if nm:
        cand = discord.utils.get(guild.text_channels, name=nm)
        if isinstance(cand, discord.TextChannel):
            return cand
    # default
    for name_try in ("💬︲ngobrol", "ngobrol", "general"):
        cand = discord.utils.get(guild.text_channels, name=name_try)
        if isinstance(cand, discord.TextChannel):
            return cand
    return None

# -------------- Public helpers --------------
async def get_banlog_thread(guild: discord.Guild) -> Optional[discord.Thread]:
    """Get or create the 'Ban Log' thread UNDER #log-botphising ONLY."""
    host = _resolve_thread_host_channel(guild)
    if not isinstance(host, discord.TextChannel):
        return None

    # Search existing threads ONLY under this host
    try:
        for th in host.threads:
            if isinstance(th, discord.Thread) and th.name == TARGET_THREAD_NAME:
                if th.archived:
                    try:
                        await th.edit(archived=False, locked=False)
                    except Exception:
                        pass
                return th
    except Exception:
        pass

    try:
        async for th in host.archived_threads(limit=50):
            if th.name == TARGET_THREAD_NAME:
                try:
                    await th.edit(archived=False, locked=False)
                except Exception:
                    pass
                return th
    except Exception as e:
        log.debug("[banlog] archived_threads fetch failed: %s", e)

    # Create new one under the correct host
    try:
        th = await host.create_thread(name=TARGET_THREAD_NAME, type=discord.ChannelType.public_thread, auto_archive_duration=10080)
        log.info("[banlog] created thread '%s' under #%s (%s)", TARGET_THREAD_NAME, getattr(host,'name','?'), getattr(host,'id','?'))
        return th
    except Exception as e:
        log.warning("[banlog] create_thread failed under #%s: %s", getattr(host, "name","?"), e)
        return None

async def send_public_ban_announcement(guild: discord.Guild, embed: discord.Embed) -> bool:
    """Send a copy of the ban embed to the public announcement channel."""
    ch = _resolve_announce_channel(guild)
    if not isinstance(ch, discord.TextChannel):
        log.warning("[banlog] announce channel not found for guild %s", getattr(guild, "name", "?"))
        return False
    try:
        await ch.send(embed=embed)
        return True
    except Exception as e:
        log.warning("[banlog] send announcement failed in #%s: %s", getattr(ch, "name","?"), e)
        return False
