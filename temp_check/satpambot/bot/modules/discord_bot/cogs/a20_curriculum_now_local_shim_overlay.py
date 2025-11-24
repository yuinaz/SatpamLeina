
from discord.ext import commands
import logging, os
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
LOG = logging.getLogger(__name__)
def _now_local(tz_name=None):
    tz= tz_name or os.getenv("SELFHEAL_RL_TZ","Asia/Jakarta")
    try:
        if ZoneInfo: return datetime.now(ZoneInfo(tz))
    except Exception: pass
    return datetime.now()
class A20NowLocalShim(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            import importlib
            a20 = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a20_curriculum_tk_sd")
            if not hasattr(a20, "_now_local"):
                setattr(a20, "_now_local", _now_local)
                LOG.info("[a20:now_local] injected")
        except Exception as e:
            LOG.debug("[a20:now_local] skip: %r", e)
async def setup(bot): await bot.add_cog(A20NowLocalShim(bot))