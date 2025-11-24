
from __future__ import annotations
import asyncio, logging
from pathlib import Path
from discord.ext import commands

log = logging.getLogger(__name__)

class FixCurriculumAutoloadPath(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._task = asyncio.create_task(self._early_loop())

    async def _early_loop(self):
        for i in range(20):
            try:
                patched = 0
                for name, cog in list(getattr(self.bot, "cogs", {}).items()):
                    try:
                        if "curriculum_autoload" in name.lower() or type(cog).__name__.lower().find("curriculum")>=0:
                            p = getattr(cog, "status_json_path", None)
                            if isinstance(p, str):
                                newp = Path(p)
                                try: newp.parent.mkdir(parents=True, exist_ok=True)
                                except Exception: pass
                                setattr(cog, "status_json_path", newp)
                                patched += 1
                                log.warning("[curriculum_autoload_fix] early-coerced %s.status_json_path -> Path(%r)", name, str(newp))
                    except Exception as e:
                        log.exception("[curriculum_autoload_fix] loop error on %s: %r", name, e)
                if patched:
                    return
            except Exception as e:
                log.exception("[curriculum_autoload_fix] loop top-level error: %r", e)
            await asyncio.sleep(0.5)
        log.info("[curriculum_autoload_fix] nothing to patch in early window")

    async def cog_unload(self):
        try: self._task.cancel()
        except Exception: pass

def _inject(bot):
    flag = "_fix_curriculum_autoload_path_overlay_loaded"
    if getattr(bot, flag, False): return
    setattr(bot, flag, True)
    try:
        bot.add_cog(FixCurriculumAutoloadPath(bot))
        log.info("[curriculum_autoload_fix] overlay loaded")
    except Exception:
        FixCurriculumAutoloadPath(bot)

def setup(bot): _inject(bot)
async def setup(bot): _inject(bot)
