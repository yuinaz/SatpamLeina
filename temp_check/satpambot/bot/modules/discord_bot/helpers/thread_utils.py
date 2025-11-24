from __future__ import annotations

import os, logging, contextlib
from typing import Optional
import discord

log = logging.getLogger(__name__)
DEFAULT_THREAD_NAME = "neuro-lite progress"

async def find_log_channel(bot: discord.Client) -> Optional[discord.TextChannel]:
    raw = os.getenv("LOG_CHANNEL_ID", "") or os.getenv("SELFHEAL_THREAD_CHANNEL_ID", "")
    try:
        cid = int(str(raw).strip()) if raw else 0
    except Exception:
        cid = 0
    if cid:
        ch = bot.get_channel(cid)
        if ch is None:
            with contextlib.suppress(Exception):
                ch = await bot.fetch_channel(cid)
        if isinstance(ch, discord.TextChannel):
            return ch

    for g in getattr(bot, "guilds", []):
        for name in ("log-botphising", "log-botphishing", "logs", "bot-logs"):
            ch = discord.utils.get(g.text_channels, name=name)
            if isinstance(ch, discord.TextChannel):
                return ch
    for g in getattr(bot, "guilds", []):
        for ch in g.text_channels:
            if isinstance(ch, discord.TextChannel):
                return ch
    return None

async def find_thread_by_name(ch: discord.TextChannel, name: str = DEFAULT_THREAD_NAME) -> Optional[discord.Thread]:
    name_l = (name or "").strip().lower()
    try:
        for th in getattr(ch, "threads", []):
            if (th.name or "").strip().lower() == name_l:
                return th
    except Exception:
        pass
    iters = []
    if hasattr(ch, "archived_threads"):
        iters.append(ch.archived_threads(limit=200))
    if hasattr(ch, "public_archived_threads"):
        iters.append(ch.public_archived_threads(limit=200))
    for itr in iters:
        try:
            async for th in itr:
                if (th.name or "").strip().lower() == name_l:
                    return th
        except Exception:
            continue
    return None

async def ensure_neuro_thread(bot: discord.Client, name: str = DEFAULT_THREAD_NAME) -> Optional[discord.Thread]:
    ch = await find_log_channel(bot)
    if not ch:
        log.warning("[thread_utils] log channel not found")
        return None
    th = await find_thread_by_name(ch, name=name)
    if th:
        return th
    try:
        if hasattr(ch, "create_thread"):
            th = await ch.create_thread(name=name, type=discord.ChannelType.public_thread, auto_archive_duration=10080)
            return th
    except Exception as e:
        log.warning("[thread_utils] failed to create thread %r: %s", name, e)
        return None
    return None
