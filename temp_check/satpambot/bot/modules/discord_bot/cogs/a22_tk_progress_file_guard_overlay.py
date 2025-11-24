
"""
a22_tk_progress_file_guard_overlay.py
- Ensures directory for a20_curriculum_tk_sd.PROGRESS_FILE exists before writing.
- If path not writeable, fallback to /tmp/learn_progress_tk.json (logged).
"""
import os, logging, importlib, pathlib
from discord.ext import commands
log = logging.getLogger(__name__)

def _ensure_path(p: str) -> str:
    try:
        path = pathlib.Path(p)
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if not path.exists():
                path.touch(exist_ok=True)
        except Exception:
            pass
        return str(path)
    except Exception as e:
        log.warning("[tk-guard] cannot prepare %s: %s", p, e)
        return "/tmp/learn_progress_tk.json"

class TKProgressFileGuardOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._guard()
    def _guard(self):
        try:
            m = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a20_curriculum_tk_sd")
        except Exception as e:
            log.warning("[tk-guard] cannot import a20_curriculum_tk_sd: %s", e)
            return
        pf = getattr(m, "PROGRESS_FILE", None)
        if isinstance(pf, str):
            fixed = _ensure_path(pf)
            if fixed != pf:
                setattr(m, "PROGRESS_FILE", fixed)
                log.info("[tk-guard] PROGRESS_FILE fallback -> %s", fixed)

async def setup(bot):
    await bot.add_cog(TKProgressFileGuardOverlay(bot))
