
from discord.ext import commands
import logging, inspect

LOG = logging.getLogger(__name__)
def _guarded(fn):
    async def w(*a, **k):
        try: return await fn(*a, **k)
        except AttributeError as e:
            if "NoneType" in str(e) and ".get" in str(e):
                LOG.info("[progress-guard] skip cycle (None.get)")
                return None
            raise
        except Exception as e:
            LOG.info("[progress-guard] skip cycle: %r", e); return None
    return w
class ProgressGuard(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            import importlib
            m = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.progress_embed_solo")
        except Exception as e:
            LOG.debug("[progress-guard] no module: %r", e); return
        for name in ("_update_once","update_once","_tick","_runner"):
            f = getattr(m, name, None)
            if f and inspect.iscoroutinefunction(f):
                setattr(m, name, _guarded(f))
                LOG.info("[progress-guard] patched %s", name)
async def setup(bot): await bot.add_cog(ProgressGuard(bot))