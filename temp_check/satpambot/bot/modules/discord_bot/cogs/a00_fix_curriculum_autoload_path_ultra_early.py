
from __future__ import annotations
import asyncio, logging
from pathlib import Path
from discord.ext import commands

log = logging.getLogger(__name__)

def _patch_obj(obj) -> bool:
    try:
        p = getattr(obj, "status_json_path", None)
        if isinstance(p, str):
            newp = Path(p)
            try: newp.parent.mkdir(parents=True, exist_ok=True)
            except Exception: pass
            setattr(obj, "status_json_path", newp)
            log.warning("[curriculum_autoload_fix] coerced status_json_path -> Path(%r)", str(newp))
            return True
    except Exception as e:
        log.exception("[curriculum_autoload_fix] patch error: %r", e)
    return False

class FixCurriculumUltraEarly(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._task = asyncio.create_task(self._scan_loop())

    async def _scan_loop(self):
        for _ in range(120):  # ~60s window
            try:
                for name, cog in list(getattr(self.bot, "cogs", {}).items()):
                    if "curriculum" in (name or "").lower() or "curriculum" in type(cog).__name__.lower():
                        if _patch_obj(cog):
                            return
            except Exception as e:
                log.exception("[curriculum_autoload_fix] scan error: %r", e)
            await asyncio.sleep(0.5)
        log.info("[curriculum_autoload_fix] scan window ended without patch")

    async def cog_unload(self):
        try: self._task.cancel()
        except Exception: pass

    @commands.Cog.listener()
    async def on_cog_add(self, cog):
        try:
            if "curriculum" in type(cog).__name__.lower() or "curriculum" in getattr(cog, "__module__", "").lower():
                if _patch_obj(cog):
                    log.info("[curriculum_autoload_fix] patched via on_cog_add: %s", type(cog).__name__)
        except Exception as e:
            log.exception("[curriculum_autoload_fix] on_cog_add error: %r", e)

def _inject(bot):
    flag = "_fix_curriculum_ultra_early_loaded"
    if getattr(bot, flag, False): return
    setattr(bot, flag, True)
    try:
        bot.add_cog(FixCurriculumUltraEarly(bot))
        log.info("[curriculum_autoload_fix] ultra-early overlay loaded")
    except Exception:
        FixCurriculumUltraEarly(bot)

def setup(bot): _inject(bot)
async def setup(bot): _inject(bot)
