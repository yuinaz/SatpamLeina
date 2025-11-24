
"""
memory_upsert_fix.py
Safe helpers for pinned memory upserts to avoid NoneType.channel errors.
Import this module in place of original memory_upsert or from it.
"""
import os
import json
import logging
from typing import Optional, Dict
import discord

LOG = logging.getLogger(__name__)

def _get_log_id() -> Optional[int]:
    raw = os.getenv("LOG_CHANNEL_ID") or os.getenv("SATPAMBOT_LOG_CHANNEL_ID")
    if not raw:
        return None
    try:
        return int(raw.strip())
    except Exception:
        return None

async def _ensure_thread(channel: discord.TextChannel, name: str) -> discord.abc.Messageable:
    # try find existing thread
    try:
        for th in channel.threads:
            if th.name.lower() == name.lower():
                return th
    except Exception:
        pass
    try:
        async for th in channel.archived_threads(limit=50):
            if th.name.lower() == name.lower():
                return th
    except Exception:
        pass
    try:
        th = await channel.create_thread(name=name, type=discord.ChannelType.public_thread)  # type: ignore
        return th
    except Exception:
        return channel

async def ensure_keeper(bot: discord.Client, title: str, thread_name: Optional[str] = None) -> Optional[discord.Message]:
    log_id = _get_log_id()
    if not log_id:
        return None
    ch = bot.get_channel(log_id)
    if not isinstance(ch, discord.TextChannel):
        return None

    dest = ch
    if thread_name:
        dest = await _ensure_thread(ch, thread_name)

    # locate pinned keeper by embed title
    try:
        pins = await dest.pins()
        for m in pins:
            if m.embeds:
                try:
                    t = (m.embeds[0].title or "").strip()
                except Exception:
                    t = ""
                if t == title.strip():
                    return m
    except Exception:
        pass

    # create new keeper
    try:
        em = discord.Embed(title=title, description="")
        msg = await dest.send(embed=em)
        await msg.pin()
        return msg
    except Exception as e:
        LOG.error("ensure_keeper failed: %r", e)
        return None

async def upsert_json(bot: discord.Client, title: str, payload: Dict, thread_name: Optional[str] = None) -> bool:
    keeper = await ensure_keeper(bot, title, thread_name)
    if not keeper:
        return False

    if getattr(keeper, "channel", None) is None:
        keeper = await ensure_keeper(bot, title, thread_name)
        if not keeper:
            return False

    try:
        pretty = "```json\n" + json.dumps(payload, indent=2, ensure_ascii=False) + "\n```"
        em = discord.Embed(title=title, description=pretty)
        await keeper.edit(embed=em)
        return True
    except Exception as e:
        LOG.error("upsert_json edit failed: %r", e)
        return False
