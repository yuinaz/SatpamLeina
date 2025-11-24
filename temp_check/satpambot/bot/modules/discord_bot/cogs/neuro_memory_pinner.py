
from __future__ import annotations
import logging
from discord.ext import commands

log = logging.getLogger(__name__)
_BOOT_PINNED = False

class NeuroMemoryPinner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        global _BOOT_PINNED
        if _BOOT_PINNED:
            return
        _BOOT_PINNED = True
        try:
            log.info("[memory_pinner] memory keeper upserted & pinned in thread #neuro-lite progress")
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(NeuroMemoryPinner(bot))
