from __future__ import annotations

from discord.ext import commands

import asyncio, time
from collections import defaultdict
from discord.ext import tasks
try:
    from satpambot.bot.modules.discord_bot.helpers import log_utils
except Exception:
    import importlib as _imp
    log_utils = _imp.import_module("satpambot.bot.modules.discord_bot.helpers.log_utils")

_last_run = defaultdict(lambda: 0.0)

def _debounce_delay() -> float:
    return 15.0  # seconds (hardcoded)

def _refresh_every() -> float:
    return 300.0  # seconds (~5 minutes, hardcoded)

class PresenceFix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._ticker.start()

    def cog_unload(self):
        try:
            self._ticker.cancel()
        except Exception:
            pass

    @tasks.loop(seconds=1.0)
    async def _ticker(self):
        # Periodic refresh to keep uptime/presence fresh without spamming
        await asyncio.sleep(_refresh_every())
        try:
            for g in list(getattr(self.bot, "guilds", []) or []):
                await log_utils.upsert_status_embed(self.bot, g)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        guild = getattr(after, "guild", None)
        if guild is None:
            return
        now = time.time()
        last = _last_run[guild.id]
        if now - last < _debounce_delay():
            return
        _last_run[guild.id] = now
        async def _task():
            try:
                await log_utils.upsert_status_embed(self.bot, guild)
            except Exception:
                pass
        asyncio.create_task(_task())
async def setup(bot):  # type: ignore[override]
    await bot.add_cog(PresenceFix(bot))