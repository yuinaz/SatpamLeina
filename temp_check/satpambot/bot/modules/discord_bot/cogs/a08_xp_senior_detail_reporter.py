
from __future__ import annotations
import logging
from discord.ext import commands
log = logging.getLogger(__name__)
def _to_int(v,d=0):
    try: return int(v)
    except Exception:
        try: return int(float(v))
        except Exception: return d
class XPSeniorDetailReporter(commands.Cog):
    def __init__(self, bot): self.bot=bot
    async def _get(self,k):
        try:
            from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
            return await UpstashClient().get_raw(k)
        except Exception as e:
            log.info("[xp-senior-detail] get %s fail: %r", k, e); return None
    async def _set(self,k,v):
        try:
            from urllib.parse import quote
            from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
            enc=quote(str(v),safe=""); await UpstashClient()._apost(f"/set/{k}/{enc}"); return True
        except Exception as e:
            log.info("[xp-senior-detail] set %s fail: %r", k, e); return False
    async def write_total(self,total:int):
        if int(total)<=0:
            log.info("[xp-senior-detail] skip non-positive total=%s", total); return False
        cur = _to_int(await self._get("xp:bot:senior_total"), -1)
        if cur==total: return False
        return await self._set("xp:bot:senior_total", str(total))
async def setup(bot): await bot.add_cog(XPSeniorDetailReporter(bot))
