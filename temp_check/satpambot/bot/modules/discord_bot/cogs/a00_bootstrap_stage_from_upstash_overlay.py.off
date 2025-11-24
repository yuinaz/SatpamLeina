
from __future__ import annotations
import os, json, logging, asyncio, urllib.parse
from discord.ext import commands
log = logging.getLogger(__name__)
def _envb(k, d=True):
    v = os.getenv(k)
    if v is None: return d
    return str(v).strip().lower() in {"1","true","on","yes"}
class UpstashLite:
    def __init__(self):
        self.base = (os.getenv("UPSTASH_REDIS_REST_URL","") or "").rstrip("/")
        self.tok  = os.getenv("UPSTASH_REDIS_REST_TOKEN","") or ""
    def ok(self): return bool(self.base and self.tok)
    async def get(self, k: str):
        if not self.ok(): return None
        import aiohttp
        async with aiohttp.ClientSession() as s:
            u = f"{self.base}/get/{urllib.parse.quote(k, safe='')}"
            async with s.get(u, headers={"Authorization": f"Bearer {self.tok}"}) as r:
                try: j = await r.json(); return j.get("result")
                except Exception: return None
class BootstrapStageFromUpstash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.enabled = _envb("BOOTSTRAP_STAGE_FROM_UPSTASH", True)
        self.us = UpstashLite()
        self._done = False
    async def _run_once(self):
        if self._done or not self.enabled or not self.us.ok(): return
        try:
            raw = await self.us.get("learning:status_json")
            if not raw: return
            data = json.loads(raw) if isinstance(raw,str) else raw
            label = str((data or {}).get("label","") or "")
            stage = (data or {}).get("stage") or {}
            cur = int(stage.get("current",0) or 0)
            req = int(stage.get("required",1) or 1)
            pct = float((data or {}).get("percent",0) or 0)
            if not label.startswith(("KULIAH-","MAGANG")): return
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            kv = PinnedJSONKV(self.bot)
            await kv.set_multi({
                "xp:stage:label": label,
                "xp:stage:current": cur,
                "xp:stage:required": req,
                "xp:stage:percent": pct,
            })
            self._done = True
            log.warning("[bootstrap-stage] restored pinned KV from Upstash: %s %s/%s (%.1f%%)", label, cur, req, pct)
        except Exception as e:
            log.debug("[bootstrap-stage] skip: %r", e)
    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        asyncio.create_task(self._run_once())
async def setup(bot):
    await bot.add_cog(BootstrapStageFromUpstash(bot))
