
import os
import logging
import discord

LOG = logging.getLogger(__name__)

def _get_focus_id() -> int:
    raw = os.getenv("LOG_CHANNEL_ID") or ""
    try:
        return int(raw)
    except Exception:
        return 0

async def _redirect_to_log(bot, *args, **kwargs):
    focus_id = _get_focus_id()
    if not focus_id:
        return None
    chan = bot.get_channel(focus_id) if bot else None
    if chan is None:
        return None
    try:
        return await chan.send(*args, **kwargs)
    except Exception:
        return None

# Keep originals
_ORIG_USER_SEND = discord.User.send
_ORIG_DM_SEND = discord.DMChannel.send

async def _user_send(self, *args, **kwargs):
    bot = getattr(getattr(self, "_state", None), "client", None)
    # Always redirect DM outbox to log channel
    await _redirect_to_log(bot, "*DM BLOCKED*", **kwargs)
    LOG.info("[dm_muzzle_strict] Redirected a DM to log channel.")
    return None

async def _dm_send(self, *args, **kwargs):
    bot = getattr(getattr(self, "_state", None), "client", None)
    await _redirect_to_log(bot, "*DM BLOCKED*", **kwargs)
    LOG.info("[dm_muzzle_strict] Redirected a DM to log channel.")
    return None

def setup(bot):
    # Idempotent monkeypatch
    if getattr(discord.User.send, "__name__", "") != "_user_send":
        discord.User.send = _user_send
    if getattr(discord.DMChannel.send, "__name__", "") != "_dm_send":
        discord.DMChannel.send = _dm_send
    LOG.info("[dm_muzzle_strict] active")
