
from __future__ import annotations
import os, logging, importlib
from discord.ext import commands

log = logging.getLogger(__name__)

# --- import-time patch: make sure a20_curriculum_tk_sd has _ensure_dir ---
def _install():
    try:
        m = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a20_curriculum_tk_sd")
        if not hasattr(m, "_ensure_dir"):
            def _ensure_dir(p: str):
                try:
                    os.makedirs(p, exist_ok=True)
                except Exception:
                    pass
            setattr(m, "_ensure_dir", _ensure_dir)
            log.info("[ensure-dir-patch] injected _ensure_dir into a20_curriculum_tk_sd (import-time)")
        else:
            log.debug("[ensure-dir-patch] _ensure_dir already present")
    except Exception as e:
        log.debug("[ensure-dir-patch] import-time patch skipped: %r", e)

_install()

class EnsureDirImportTimeOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # re-assert on_ready just in case a20 imported late by other loaders
        try:
            _install()
        except Exception as e:
            log.debug("[ensure-dir-patch] on_ready re-assert failed: %r", e)

async def setup(bot):
    await bot.add_cog(EnsureDirImportTimeOverlay(bot))
