
from __future__ import annotations
import logging, asyncio
from typing import Optional
from discord.ext import commands
log = logging.getLogger(__name__)
def _cfg_int(key: str, default: int = 0):
    try:
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_int
        return int(cfg_int(key, default))
    except Exception: return int(default)
def _cfg_str(key: str, default: str = ""):
    try:
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_str
        return str(cfg_str(key, default))
    except Exception: return str(default)
class LadderAutoSeedOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.enabled = (_cfg_int("LADDER_AUTOSEED", 0) == 1)
        log.info("[ladder_autoseed] %s", "enabled" if self.enabled else "disabled")
    async def rtype(self,key: str)->Optional[str]:
        try:
            import httpx
            url=_cfg_str("UPSTASH_REDIS_REST_URL","").rstrip("/")
            tok=_cfg_str("UPSTASH_REDIS_REST_TOKEN","")
            if not url or not tok: return None
            timeout=httpx.Timeout(3.0, connect=2.0, read=2.0, write=2.0)
            limits=httpx.Limits(max_connections=2, max_keepalive_connections=1)
            async with httpx.AsyncClient(timeout=timeout, limits=limits) as cli:
                r=await cli.get(f"{url}/type/{key}", headers={"Authorization": f"Bearer {tok}"})
                if r.status_code!=200: return None
                return str(r.json().get("result"))
        except Exception: return None
    async def _task(self):
        if not self.enabled: return
        keys=["xp:ladder:SMP","xp:ladder:KULIAH","xp:ladder:MAGANG"]
        need=[]
        for k in keys:
            t=await self.rtype(k)
            if t is None: return
            if t.upper()=="NONE": need.append(k)
        if not need: return
        from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
        from urllib.parse import quote
        cli=UpstashClient()
        async def set_if_none(k, payload):
            try:
                enc=quote(payload, safe=""); await cli._apost(f"/set/{k}/{enc}")
                log.warning("[ladder_autoseed] seeded %s", k)
            except Exception: pass
        SMP_DEF='["SMP-L1","2000","SMP-L2","4000","SMP-L3","8000"]'
        KUL_DEF='["S1","19000","S2","35000","S3","58000","S4","70000","S5","96500","S6","158000","S7","220000","S8","262500"]'
        MAG_DEF='["1TH","2000000"]'
        if "xp:ladder:SMP" in need: await set_if_none("xp:ladder:SMP", SMP_DEF)
        if "xp:ladder:KULIAH" in need: await set_if_none("xp:ladder:KULIAH", KUL_DEF)
        if "xp:ladder:MAGANG" in need: await set_if_none("xp:ladder:MAGANG", MAG_DEF)
    @commands.Cog.listener()
    async def on_ready(self):
        if not self.enabled: return
        await self.bot.wait_until_ready(); await asyncio.sleep(1.0); await self._task()
async def setup(bot): await bot.add_cog(LadderAutoSeedOverlay(bot))
