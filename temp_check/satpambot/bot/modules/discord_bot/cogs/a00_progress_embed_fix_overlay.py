from __future__ import annotations

# a00_progress_embed_fix_overlay.py

from discord.ext import commands
import sys, logging, inspect, types

log = logging.getLogger(__name__)

def _wrap_sync_to_async(f):
    async def _wrapped(*a, **kw):
        return f(*a, **kw)
    _wrapped.__name__ = f"{f.__name__}_asyncwrap"
    return _wrapped

def _patch_progress_embed_solo():
    patched = 0
    for modname, mod in list(sys.modules.items()):
        if not isinstance(mod, types.ModuleType):
            continue
        if hasattr(mod, "progress_embed_solo"):
            fn = getattr(mod, "progress_embed_solo")
            if inspect.iscoroutinefunction(fn):
                continue
            try:
                setattr(mod, "progress_embed_solo", _wrap_sync_to_async(fn))
                patched += 1
            except Exception:
                pass
    if patched:
        log.info("[prog-embed-fix] patched progress_embed_solo in %d module(s)", patched)

class ProgressEmbedFix(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        _patch_progress_embed_solo()
async def setup(bot: commands.Bot):
    await bot.add_cog(ProgressEmbedFix(bot))