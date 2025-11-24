from __future__ import annotations

import os, logging
import discord
from typing import Optional

log = logging.getLogger(__name__)

def _get_id(name: str) -> Optional[int]:
    v = os.getenv(name, "").strip()
    if not v:
        return None
    try:
        return int(v)
    except Exception:
        return None

LOG_CHANNEL_ID = _get_id("LOG_CHANNEL_ID") or _get_id("LOG_CHANNEL_ID_RAW")
LOG_THREAD_ID = _get_id("LOG_THREAD_ID")
ERROR_LOG_CHANNEL_ID = _get_id("ERROR_LOG_CHANNEL_ID")

async def resolve_log_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    if not guild:
        return None
    if LOG_CHANNEL_ID:
        ch = guild.get_channel(LOG_CHANNEL_ID)
        if isinstance(ch, discord.TextChannel):
            return ch
    # fallback: find by name from env LOG_CHANNEL_NAME
    name = (os.getenv("LOG_CHANNEL_NAME","") or "").strip().lower()
    if name:
        for ch in getattr(guild, "text_channels", []):
            if ch.name.lower() == name:
                return ch
    return None

async def resolve_error_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    if not guild:
        return None
    if ERROR_LOG_CHANNEL_ID:
        ch = guild.get_channel(ERROR_LOG_CHANNEL_ID)
        if isinstance(ch, discord.TextChannel):
            return ch
    # fallback by name
    name = (os.getenv("ERROR_LOG_CHANNEL_NAME","") or "").strip().lower()
    if name:
        for ch in getattr(guild, "text_channels", []):
            if ch.name.lower() == name:
                return ch
    return None

async def maybe_thread(channel: discord.TextChannel) -> discord.abc.Messageable:
    # If a thread ID is supplied, prefer sending into that thread if it exists in the channel
    try:
        if LOG_THREAD_ID:
            th = channel.guild.get_channel(LOG_THREAD_ID)
            if th and getattr(th, "parent_id", None) == channel.id:
                return th
    except Exception:
        pass
    return channel

async def send_embed(guild: discord.Guild, embed: discord.Embed):
    try:
        ch = await resolve_log_channel(guild)
        if not ch:
            return
        dst = await maybe_thread(ch)
        await dst.send(embed=embed)
    except Exception as e:
        log.debug("send_embed failed: %s", e)

async def send_text(guild: discord.Guild, content: str):
    try:
        ch = await resolve_log_channel(guild)
        if not ch:
            return
        dst = await maybe_thread(ch)
        await dst.send(content)
    except Exception as e:
        log.debug("send_text failed: %s", e)

async def send_error(guild: discord.Guild, embed: Optional[discord.Embed] = None, content: Optional[str] = None):
    try:
        ch = await resolve_error_channel(guild)
        if not ch:
            # fallback to main log channel if error channel not set
            ch = await resolve_log_channel(guild)
        if not ch:
            return
        if embed:
            await ch.send(embed=embed)
        elif content:
            await ch.send(content)
    except Exception as e:
        log.debug("send_error failed: %s", e)
