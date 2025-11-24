
from discord.ext import commands
import os, logging, importlib
log = logging.getLogger(__name__)

def _prefer_senior() -> bool:
    return (os.getenv("CURRICULUM_FORCE_SENIOR","0") == "1") or            (os.getenv("CURRICULUM_PREF","").lower() == "senior") or            (os.getenv("CURRICULUM_PREFERRED_TRACK","").lower() == "senior")

class _Guard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if _prefer_senior():
            try:
                # If autoload already loaded, make it no-op
                m = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a21_curriculum_autoload")
                if hasattr(m, "CurriculumAutoload"):
                    def _noop(*a, **k): pass
                    try:
                        m.CurriculumAutoload.on_ready = _noop  # type: ignore[attr-defined]
                        log.info("[curriculum_guard] patched CurriculumAutoload.on_ready -> noop (prefer senior)")
                    except Exception: pass
            except Exception as e:
                log.debug("[curriculum_guard] skip patch: %r", e)

async def setup(bot):
    await bot.add_cog(_Guard(bot))
