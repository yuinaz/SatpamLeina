
from __future__ import annotations
import os, logging, asyncio
from discord.ext import commands

log = logging.getLogger(__name__)

class PhaseStrictKuliahOnlyOverlay(commands.Cog):
    """Force-only Kuliah phase; ensure MAGANG/WORK/GOV env are off at runtime too."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Set env guards (some modules may re-read os.getenv)
        for k in ("MAGANG_ENABLE", "WORK_ENABLE", "GOVERNOR_ENABLE", "PHASE_TRANSITION_ENABLE"):
            os.environ[k] = os.getenv(k, "0")
        log.info("[phase-gate] Kuliah-only enforced (MAGANG/WORK/GOV disabled)")

async def setup(bot: commands.Bot):
    await bot.add_cog(PhaseStrictKuliahOnlyOverlay(bot))
