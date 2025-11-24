import asyncio
from typing import Optional
try:
    # Prefer bot-side log utils if available
    from ...discord_bot.helpers.log_utils import find_text_channel, MOD_CMD_NAME
except Exception:
    find_text_channel = None
    MOD_CMD_NAME = "mod-command"

async def log_violation(message, image_hash: str, reason: str = ""):
    """Write a simple violation line to mod-command channel if present."""
    try:
        if find_text_channel:
            ch = find_text_channel(getattr(message, "guild", None), MOD_CMD_NAME)
            if ch:
                await ch.send(f"[VIOLATION] {message.author} — {reason} — {image_hash}")
    except Exception:
        # swallow all logging errors
        pass

async def log_image_event(message, note: str = ""):
    """Write a simple image event line to mod-command channel if present."""
    try:
        if find_text_channel:
            ch = find_text_channel(getattr(message, "guild", None), MOD_CMD_NAME)
            if ch:
                await ch.send(f"[IMAGE] {message.author}: {note}")
    except Exception:
        pass
