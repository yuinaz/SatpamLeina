from __future__ import annotations
import logging
from discord.ext import commands
from satpambot.bot.modules.discord_bot.helpers.intish import parse_intish
log = logging.getLogger(__name__)
class IntishMonkeypatchOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
            _orig_get_int = UpstashClient.get_int
            async def _patched(self, key: str, default: int=0):
                try:
                    raw = await self.get_raw(key)
                    ok, val = parse_intish(raw)
                    return int(val if ok and val is not None else default)
                except Exception:
                    return int(default)
            UpstashClient.get_int = _patched
            log.info("[intish-monkey] UpstashClient.get_int patched for intish tolerance")
        except Exception as e:
            log.debug("[intish-monkey] skip patch: %r", e)
async def setup(bot): await bot.add_cog(IntishMonkeypatchOverlay(bot))
def setup(bot):
    try: bot.add_cog(IntishMonkeypatchOverlay(bot))
    except Exception: pass