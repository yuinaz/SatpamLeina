from __future__ import annotations

from discord.ext import commands

# satpambot/bot/modules/discord_bot/cogs/thread_exemptor.py
# Global thread exemption layer.
# This cog wraps every other cog's on_message handler so that **messages posted in Threads**
# are ignored by moderation cogs (no ban / no delete / no scans).
#
# No ENV needed. Drop-in file only.

import inspect
from typing import Any, Callable, Coroutine, Optional

import discord

WRAP_ATTR = "_thread_exempt_wrapped"

def _make_wrapper(orig: Callable[..., Coroutine[Any, Any, Any]]):
    async def _wrapped(self, message: discord.Message, *a, **kw):
        # DM and Guild checks are left to original handler; we only gate for Threads.
        if isinstance(message.channel, discord.Thread):
            return  # hard stop: threads are free zone
        return await orig(self, message, *a, **kw)
    setattr(_wrapped, WRAP_ATTR, True)
    setattr(_wrapped, "__name__", getattr(orig, "__name__", "on_message"))
    return _wrapped

class ThreadExemptor(commands.Cog):
    """Middleware-style cog that enforces *Thread Free Zone*.


    Once the bot is ready, it scans all loaded cogs and wraps their `on_message`

    listener (if any) so that events coming from `discord.Thread` channels are ignored.

    This affects **all cogs** uniformly without editing each one.

    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._patched = False

    @commands.Cog.listener()
    async def on_ready(self):
        # Run once, after all cogs are loaded and the bot is ready.
        if self._patched:
            return

        for name, cog in list(self.bot.cogs.items()):
            # Don't wrap ourselves
            if isinstance(cog, ThreadExemptor):
                continue

            # Find a method actually named 'on_message' (common pattern for listeners)
            meth = getattr(cog, "on_message", None)
            if meth is None:
                continue

            # Skip if already wrapped
            if getattr(meth, WRAP_ATTR, False):
                continue

            # Only wrap coroutine functions with signature (self, message, ...)
            try:
                sig = inspect.signature(meth)
                params = list(sig.parameters.values())
                if not params or params[0].name != "self":
                    # unexpected method shape, skip
                    continue
            except (TypeError, ValueError):
                continue

            wrapped = _make_wrapper(meth)
            setattr(cog, "on_message", wrapped)

        self._patched = True
async def setup(bot: commands.Bot):
    await bot.add_cog(ThreadExemptor(bot))