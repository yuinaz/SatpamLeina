from __future__ import annotations
import os, logging, importlib
from discord.ext import commands

log = logging.getLogger(__name__)

def _ensure_dir(path: str):
    if not path:
        return ""
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass
    return path

class EnsureDirPatchOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Try patching curriculum module that expects _ensure_dir
        for modname in (
            "satpambot.bot.modules.discord_bot.cogs.a20_curriculum_tk_sd",
            "satpambot.bot.modules.discord_bot.cogs.a21_curriculum_autoload",
        ):
            try:
                m = importlib.import_module(modname)
                if not hasattr(m, "_ensure_dir"):
                    setattr(m, "_ensure_dir", _ensure_dir)
                    log.warning("[ensure-dir-patch] injected _ensure_dir into %s", modname)
            except Exception as e:
                log.debug("[ensure-dir-patch] skip %s: %r", modname, e)

async def setup(bot):
    await bot.add_cog(EnsureDirPatchOverlay(bot))

def setup(bot):
    try:
        bot.add_cog(EnsureDirPatchOverlay(bot))
    except Exception:
        pass