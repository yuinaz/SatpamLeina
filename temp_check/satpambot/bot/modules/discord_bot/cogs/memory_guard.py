from __future__ import annotations

from discord.ext import commands

# -*- coding: utf-8 -*-
"""
memory_guard.py
----------------
Monitor penggunaan memori proses dan tulis peringatan di log.
Tidak memaksa restart; ini pengawas ringan agar mudah diagnosis.

Ubah interval & ambang sesuai kebutuhan.
"""

import asyncio
import logging

from discord.ext import commands, tasks

LOG = logging.getLogger(__name__)

INTERVAL_SEC = 12
SOFT_MB = 420
HARD_MB = 480

def _get_mem_mb() -> int:
    try:
        import psutil, os

        p = psutil.Process(os.getpid())
        return int(p.memory_info().rss / (1024*1024))
    except Exception:
        return -1

class MemoryGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task = self._loop.start()

    @tasks.loop(seconds=INTERVAL_SEC)
    async def _loop(self):
        mb = _get_mem_mb()
        if mb < 0:
            return
        if mb >= HARD_MB:
            LOG.error("[memory-guard] HARD threshold terlampaui: %dMB (hard=%dMB)", mb, HARD_MB)
        elif mb >= SOFT_MB:
            LOG.warning("[memory-guard] Soft threshold terlampaui: %dMB (soft=%dMB)", mb, SOFT_MB)
        else:
            LOG.debug("[memory-guard] OK: %dMB", mb)

    @commands.Cog.listener()
    async def on_ready(self):
        LOG.info("[memory-guard] started (interval=%ss soft=%dMB hard=%dMB)", INTERVAL_SEC, SOFT_MB, HARD_MB)
async def setup(bot: commands.Bot):
    await bot.add_cog(MemoryGuard(bot))