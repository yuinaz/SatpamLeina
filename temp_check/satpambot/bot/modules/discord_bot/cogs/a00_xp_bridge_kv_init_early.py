
from __future__ import annotations
import logging, asyncio
from discord.ext import commands
log = logging.getLogger(__name__)
def _cfg_int(k,d=0):
    try:
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_int
        return int(cfg_int(k,d))
    except Exception: return int(d)
def _to_int(v,d=0):
    try: return int(v)
    except Exception:
        try: return int(float(v))
        except Exception: return d
class XPBridgeKVInitEarly(commands.Cog):
    def __init__(self, bot): self.bot=bot
    async def _get(self,key):
        try:
            from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
            return await UpstashClient().get_raw(key)
        except Exception as e:
            log.info("[xp-kv-init] get %s fail: %r", key, e); return None
    async def _set(self,key,val):
        try:
            from urllib.parse import quote
            from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
            enc = quote(str(val), safe=""); await UpstashClient()._apost(f"/set/{key}/{enc}"); return True
        except Exception as e:
            log.info("[xp-kv-init] set %s fail: %r", key, e); return False
    def _pinned_total(self):
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            kv = PinnedJSONKV(self.bot).get_map()
            n = _to_int(kv.get("xp:bot:senior_total"), -1)
            return n if n>=0 else None
        except Exception: return None
    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        cur = _to_int(await self._get("xp:bot:senior_total"), -1)
        if cur>=0:
            log.info("[xp-kv-init] senior_total exists -> %s", cur); return
        p = self._pinned_total()
        if p is not None:
            if await self._set("xp:bot:senior_total", str(p)):
                log.warning("[xp-kv-init] restored senior_total from pinned -> %s", p)
            return
        if _cfg_int("XP_FORCE_RESET_ON_BOOT",0)==1:
            if await self._set("xp:bot:senior_total","0"):
                log.warning("[xp-kv-init] forced reset to 0"); return
        log.info("[xp-kv-init] unknown senior_total; skip reset (safe no-op)")
async def setup(bot): await bot.add_cog(XPBridgeKVInitEarly(bot))
