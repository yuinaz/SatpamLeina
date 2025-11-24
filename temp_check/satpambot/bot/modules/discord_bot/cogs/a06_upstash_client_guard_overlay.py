
from discord.ext import commands
import logging, importlib

LOG = logging.getLogger(__name__)
def _wrap_client(mod):
    if not hasattr(mod, "UpstashClient"): return
    cls = mod.UpstashClient
    orig_get_raw = cls.get_raw
    async def get_raw_safe(self, key):
        try:
            data = await orig_get_raw(self, key)
            return data or {}
        except Exception as e:
            LOG.debug("[upstash-safe] get_raw error: %r", e)
            return {}
    cls.get_raw = get_raw_safe
    orig_get_json = cls.get_json
    async def get_json_safe(self, key):
        data = await get_raw_safe(self, key)
        return data if isinstance(data, dict) else {}
    cls.get_json = get_json_safe
class UpstashClientGuard(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            m = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a06_upstash_client")
            _wrap_client(m)
            LOG.info("[upstash-safe] client guarded")
        except Exception as e:
            LOG.debug("[upstash-safe] skip: %r", e)
async def setup(bot): await bot.add_cog(UpstashClientGuard(bot))