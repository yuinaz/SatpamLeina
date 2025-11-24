from __future__ import annotations

from discord.ext import commands
import os, logging

LOG = logging.getLogger(__name__)

class ForceSyncOnce(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._did = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._did: return
        if str(os.getenv("FORCE_REPO_SYNC","true")).lower() not in {"1","true","yes","on"}:
            return
        try:
            await self.bot.tree.sync()
            LOG.info("[force-sync] app command tree synced")
        except Exception as e:
            LOG.exception("[force-sync] failed: %r", e)
        self._did = True
async def setup(bot):
    res = await bot.add_cog(ForceSyncOnce(bot))
    import asyncio as _aio
    if _aio.iscoroutine(res): await res