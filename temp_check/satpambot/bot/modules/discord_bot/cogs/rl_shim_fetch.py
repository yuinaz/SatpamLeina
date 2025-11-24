
# Throttle high-risk Discord HTTP calls to avoid per-channel 429 at startup.
# - Patches TextChannel.fetch_message (GET /channels/{id}/messages/{message.id})
# - Patches Message.edit (PATCH /channels/{id}/messages/{message.id})
# Non-invasive: no config keys required. Uses env 'RL_FETCH_MIN_INTERVAL' (optional).
from discord.ext import commands
import os
import time
import asyncio
import logging
from collections import defaultdict

import discord

log = logging.getLogger("satpambot.rl_shim_fetch")

_locks = defaultdict(asyncio.Lock)
_last = defaultdict(float)

def _interval():
    try:
        return max(0.2, float(os.getenv("RL_FETCH_MIN_INTERVAL", "0.7")))
    except Exception:
        return 0.7

async def _throttle_for_channel(chan_id: int):
    lock = _locks[chan_id]
    async with lock:
        now = time.monotonic()
        delta = now - _last[chan_id]
        need = _interval() - delta
        if need > 0:
            await asyncio.sleep(need)
        _last[chan_id] = time.monotonic()

class RLShimFetch(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._patched = False
        self._patch_methods()

    def _patch_methods(self):
        if getattr(discord.TextChannel.fetch_message, "_rl_shim_patched", False):
            self._patched = True
            return

        orig_fetch = discord.TextChannel.fetch_message

        async def fetch_wrapper(self, id, *args, **kwargs):  # type: ignore[override]
            try:
                await _throttle_for_channel(self.id)
            except Exception:
                pass
            return await orig_fetch(self, id, *args, **kwargs)

        fetch_wrapper._rl_shim_patched = True  # type: ignore[attr-defined]
        discord.TextChannel.fetch_message = fetch_wrapper  # type: ignore[assignment]

        # Patch Message.edit as well (some cogs prefer editing same message rapidly)
        orig_edit = discord.Message.edit

        async def edit_wrapper(self, *args, **kwargs):  # type: ignore[override]
            chan = getattr(self, "channel", None)
            chan_id = getattr(chan, "id", 0) or 0
            if chan_id:
                try:
                    await _throttle_for_channel(chan_id)
                except Exception:
                    pass
            return await orig_edit(self, *args, **kwargs)

        edit_wrapper._rl_shim_patched = True  # type: ignore[attr-defined]
        discord.Message.edit = edit_wrapper  # type: ignore[assignment]

        self._patched = True
        log.info("[rl_shim_fetch] patched TextChannel.fetch_message and Message.edit (min_interval=%.2fs)", _interval())
async def setup(bot: commands.Bot):
    await bot.add_cog(RLShimFetch(bot))