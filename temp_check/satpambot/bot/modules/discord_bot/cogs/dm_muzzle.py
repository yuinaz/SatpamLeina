"""
Cog: dm_muzzle
Blocks or redirects *all* DM sends when enabled via env DM_MUZZLE=1.

- If DM_MUZZLE=1: any attempt to send to a DM channel is dropped (or redirected to LOG_CHANNEL_ID if set).
- If DM_MUZZLE=log: redirect DM messages to LOG_CHANNEL_ID instead of sending DMs.
- Otherwise: no-op.

Safe to keep loaded at all times. No impact when DM_MUZZLE unset.
"""
from __future__ import annotations

from discord.ext import commands

import os, logging, asyncio, contextlib, inspect
from typing import Any, Optional

import discord

log = logging.getLogger(__name__)

REDIRECT_MODES = {"1", "true", "yes", "on", "drop", "block", "mute"}
LOG_MODE = {"log", "redirect"}

class _DummyMessage:
    __slots__ = ("id", "content", "channel", "author", "jump_url")
    def __init__(self, channel, content: str = ""):
        self.id = 0
        self.content = content
        self.channel = channel
        self.author = None
        self.jump_url = ""

async def _send_to_log(bot: commands.Bot, content: Optional[str] = None, embed: Optional[discord.Embed] = None, **kwargs):
    log_chan_id = int(os.getenv("LOG_CHANNEL_ID_RAW") or os.getenv("LOG_CHANNEL_ID", "0"))
    if not log_chan_id:
        return False
    chan = bot.get_channel(log_chan_id)
    if chan is None:
        with contextlib.suppress(Exception):
            chan = await bot.fetch_channel(log_chan_id)
    if chan is None:
        log.warning("[dm_muzzle] LOG_CHANNEL_ID=%r not found; cannot redirect DM", log_chan_id)
        return False
    try:
        await chan.send(content=content, embed=embed)
        return True
    except Exception as e:
        log.warning("[dm_muzzle] failed redirect DM to log: %r", e)
        return False
async def setup(bot: commands.Bot):
    mode = (os.getenv("DM_MUZZLE") or "").strip().lower()
    if not mode:
        log.info("[dm_muzzle] inactive (DM_MUZZLE not set)")
        return

    original_send = discord.abc.Messageable.send

    async def patched_send(self, *args: Any, **kwargs: Any):
        # We will block sends *only* if this messageable is a DM channel or User/Member (which resolves to DM)
        is_dm_target = isinstance(self, discord.DMChannel) or getattr(self, "type", None) == discord.ChannelType.private
        # Some code calls Member/User.send(); in that case `self` is a User/Member. Treat as DM.
        if isinstance(self, (discord.User, discord.Member)):
            is_dm_target = True

        if not is_dm_target:
            return await original_send(self, *args, **kwargs)

        # Determine content for logging/redirect
        content = None
        embed = None
        if args:
            # first positional may be content
            content = args[0] if isinstance(args[0], str) else None
        content = kwargs.get("content", content)
        embed = kwargs.get("embed")
        try:
            preview = (content or "").strip()
            if len(preview) > 150:
                preview = preview[:147] + "..."
        except Exception:
            preview = "<binary/unknown>"

        if mode in REDIRECT_MODES:
            log.info("[dm_muzzle] BLOCKED a DM send (preview=%r).", preview)
            # Drop the DM quietly and return a dummy message to avoid breaking code paths that expect a Message.
            return _DummyMessage(channel=self, content=content or "")
        elif mode in LOG_MODE:
            # Redirect to log channel if available; if not, drop.
            redirected = await _send_to_log(bot, content=content, embed=embed)
            if redirected:
                log.info("[dm_muzzle] Redirected a DM to log channel.")
                return _DummyMessage(channel=self, content=content or "")
            log.info("[dm_muzzle] LOG_MODE set but no log channel available; dropping DM.")
            return _DummyMessage(channel=self, content=content or "")
        else:
            # Unknown value: be safe and do nothing
            log.info("[dm_muzzle] unknown DM_MUZZLE=%r; staying inactive", mode)
            return await original_send(self, *args, **kwargs)

    # Monkey-patch
    discord.abc.Messageable.send = patched_send  # type: ignore[attr-defined]
    log.warning("[dm_muzzle] ACTIVE with mode=%r — DMs will not reach users.", mode)