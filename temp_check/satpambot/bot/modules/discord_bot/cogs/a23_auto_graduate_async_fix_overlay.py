
from __future__ import annotations
import asyncio, logging
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

class AutoGraduateAsyncFixOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._patch()

    def _patch(self):
        try:
            from satpambot.bot.modules.discord_bot.cogs import a23_auto_graduate_overlay as mod
            async def _check_loop(self2):
                try:
                    from satpambot.bot.modules.discord_bot.helpers.phase_utils import get_phase
                    phase = await asyncio.to_thread(get_phase)
                    if hasattr(mod, "_after_phase_resolved"):
                        try:
                            await mod._after_phase_resolved(self2, phase)  # type: ignore
                        except Exception:
                            pass
                except Exception as e:
                    log.warning("[auto-graduate-fix] check_loop error: %r", e)
                    await asyncio.sleep(2.0)
            if hasattr(mod, "check_loop"):
                try:
                    l = mod.check_loop
                    if isinstance(l, tasks.Loop):
                        l.cancel()
                except Exception:
                    pass
                mod.check_loop = tasks.loop(seconds=60)(_check_loop)  # type: ignore
                log.info("[auto-graduate-fix] patched check_loop to use asyncio.to_thread(get_phase)")
        except Exception as e:
            log.debug("[auto-graduate-fix] patch failed: %r", e)

    @commands.Cog.listener()
    async def on_ready(self):
        pass

async def setup(bot):
    await bot.add_cog(AutoGraduateAsyncFixOverlay(bot))
