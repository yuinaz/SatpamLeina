from discord.ext import commands
import logging, asyncio

try:
    from ...config import envcfg
except Exception:
    envcfg = None

log = logging.getLogger("satpambot.memory_tuner")

class MemoryTuner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(2)
        if not envcfg:
            log.info("[memory_tuner] envcfg not found; skip")
            return
        soft, hard = envcfg.memory_thresholds_mb()
        cg = self.bot.get_cog("MemoryGuard")
        if not cg:
            log.info("[memory_tuner] MemoryGuard not found; skip")
            return
        updated = False
        for meth in ("set_thresholds","configure","set_limits"):
            fn = getattr(cg, meth, None)
            if callable(fn):
                try:
                    fn(soft_mb=soft, hard_mb=hard); updated = True; break
                except TypeError:
                    try: fn(soft, hard); updated = True; break
                    except Exception: pass
        if not updated:
            try:
                if hasattr(cg, "soft_mb"): setattr(cg, "soft_mb", soft); updated = True
                if hasattr(cg, "hard_mb"): setattr(cg, "hard_mb", hard); updated = True
            except Exception:
                pass
        log.info("[memory_tuner] applied memory profile: soft=%sMB hard=%sMB (updated=%s)", soft, hard, updated)
async def setup(bot: commands.Bot):
    await bot.add_cog(MemoryTuner(bot))