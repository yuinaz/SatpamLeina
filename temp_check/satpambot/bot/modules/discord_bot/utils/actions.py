from __future__ import annotations

# modules/discord_bot/utils/actions.py
import os, logging
from typing import Optional
import discord

from .mod_guard import claim

log = logging.getLogger("actions")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))

def get_log_channel(guild: Optional[discord.Guild]) -> Optional[discord.TextChannel]:
    if not guild or not LOG_CHANNEL_ID:
        return None
    ch = guild.get_channel(LOG_CHANNEL_ID)
    return ch if isinstance(ch, discord.TextChannel) else None

async def send_log_for_message(message: discord.Message, content: str = None, embed: Optional[discord.Embed] = None):
    ch = get_log_channel(message.guild)
    if ch is None:
        # fallback to same channel if allowed
        try:
            if embed:
                await message.channel.send(embed=embed)
            elif content:
                await message.channel.send(content)
        except Exception:
            pass
        return
    try:
        if embed:
            await ch.send(embed=embed)
        elif content:
            await ch.send(content)
    except Exception:
        pass

async def delete_message_safe(message: discord.Message, actor: str = "Unknown") -> bool:
    if not claim(message.id, actor):
        return False
    try:
        await message.delete()
        return True
    except Exception as e:
        log.debug("delete_message_safe failed: %s", e)
        return False

async def timeout_member_safe(message: discord.Message, minutes: int = 10, reason: str = None, actor: str = "Unknown") -> bool:
    if not claim(message.id, actor):
        return False
    try:
        if message.guild and isinstance(message.author, discord.Member):
            await message.author.timeout(discord.utils.utcnow() + discord.timedelta(minutes=minutes), reason=reason or f"action by {actor}")
        return True
    except Exception as e:
        log.debug("timeout_member_safe failed: %s", e)
        return False

async def kick_member_safe(message: discord.Message, reason: str = None, actor: str = "Unknown") -> bool:
    if not claim(message.id, actor):
        return False
    try:
        if message.guild and isinstance(message.author, discord.Member):
            await message.guild.kick(message.author, reason=reason or f"action by {actor}")
        return True
    except Exception as e:
        log.debug("kick_member_safe failed: %s", e)
        return False
