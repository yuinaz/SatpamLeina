from __future__ import annotations

import discord
from . import static_cfg

BAN_THREAD_NAME = "Ban Log"

async def get_log_channel(guild: "discord.Guild"):
    name = getattr(static_cfg, "LOG_CHANNEL_NAME", "log-botphising").lower()
    ch = discord.utils.get(guild.text_channels, name=name)
    return ch or guild.system_channel

async def ensure_ban_thread(guild_or_channel):
    if hasattr(guild_or_channel, "send"):
        channel = guild_or_channel
    else:
        channel = await get_log_channel(guild_or_channel)
    if channel is None:
        return None
    # try existing threads
    try:
        for th in getattr(channel, "threads", []):
            if (getattr(th, "name", "") or "").lower() == BAN_THREAD_NAME.lower():
                return th
    except Exception:
        pass
    # create if missing
    try:
        th = await channel.create_thread(name=BAN_THREAD_NAME, auto_archive_duration=10080)  # 7 days
        return th
    except Exception:
        return channel
