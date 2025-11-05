from __future__ import annotations
import logging, asyncio, importlib
from typing import Optional
from discord.ext import commands

log = logging.getLogger(__name__)

def _import_upstash_client():
    for modname in (
        "satpambot.store.upstash_client",
        "satpambot.bot.store.upstash_client",
        "satpambot.bot.modules.store.upstash_client",
    ):
        try:
            mod = importlib.import_module(modname)
            cls = getattr(mod, "UpstashClient", None)
            if cls: return cls
        except Exception:
            pass
    return None

class PassiveTotalOffsetOverlay(commands.Cog):
    """Read senior_total safely using UpstashClient.get_raw/get (never .cmd)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task: Optional[asyncio.Task] = None

    async def cog_load(self):
        try:
            self._task = asyncio.create_task(self._loop())
        except Exception:
            self._task = None

    async def cog_unload(self):
        t = self._task
        self._task = None
        if t:
            t.cancel()
            try:
                await t
            except Exception:
                pass

    async def _loop(self):
        while True:
            await self.refresh()
            await asyncio.sleep(300)  # 5 minutes

    async def refresh(self):
        try:
            UpstashClient = _import_upstash_client()
            if not UpstashClient:
                log.warning("[passive-total-offset] UpstashClient not found")
                return
            us = UpstashClient()
            total = None
            if hasattr(us, "get_raw"):
                total = await us.get_raw("xp:bot:senior_total")
            elif hasattr(us, "get"):
                total = await us.get("xp:bot:senior_total")
            else:
                log.warning("[passive-total-offset] UpstashClient lacks get_raw/get")
                return
            log.debug("[passive-total-offset] senior_total=%s", total)
        except Exception as e:
            log.warning("[passive-total-offset] refresh fail: %r", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(PassiveTotalOffsetOverlay(bot))
