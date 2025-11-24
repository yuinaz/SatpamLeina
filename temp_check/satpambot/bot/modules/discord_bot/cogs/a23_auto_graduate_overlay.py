from __future__ import annotations

from discord.ext import commands
import asyncio, logging, os

from discord.ext import tasks
from satpambot.bot.modules.discord_bot.helpers.phase_utils import get_phase, set_phase, get_tk_total

log = logging.getLogger(__name__)

TK_REQUIRED_XP = int(os.getenv("TK_REQUIRED_XP", "1500"))

class AutoGraduateOverlay(commands.Cog):
    """Otomatis naik dari TK ke Senior tanpa gate."""
    def __init__(self, bot):
        self.bot = bot
        self.check_loop.start()

    def cog_unload(self):
        try: self.check_loop.cancel()
        except Exception: pass

    async def _ensure_senior_loaded(self):
        target_mod = "satpambot.bot.modules.discord_bot.cogs.learning_curriculum_senior"
        if "SeniorLearningPolicy" in self.bot.cogs:
            return
        try:
            await self.bot.load_extension(target_mod)
            log.info("[auto-graduate] SeniorLearningPolicy loaded via load_extension")
        except Exception:
            mod = __import__(target_mod, fromlist=['*'])
            for attr in dir(mod):
                if attr.lower() == "seniorlearningpolicy":
                    klass = getattr(mod, attr)
                    await self.bot.add_cog(klass(self.bot))
                    log.info("[auto-graduate] SeniorLearningPolicy loaded via add_cog")
                    break

    @tasks.loop(minutes=2.0)
    async def check_loop(self):
        try:
            phase = get_phase()
            if phase.lower() == "senior":
                return
            tk = get_tk_total()
            if tk >= TK_REQUIRED_XP:
                set_phase("senior")
                await self._ensure_senior_loaded()
                log.info("[auto-graduate] Promoted to SENIOR (tk_xp=%s)", tk)
        except Exception as e:
            log.warning("[auto-graduate] check failed: %r", e)

    @check_loop.before_loop
    async def _wait_ready(self):
        await self.bot.wait_until_ready()
async def setup(bot):
    await bot.add_cog(AutoGraduateOverlay(bot))