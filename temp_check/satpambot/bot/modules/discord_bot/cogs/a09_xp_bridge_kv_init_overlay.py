from discord.ext import commands

# a09_xp_bridge_kv_init_overlay.py
import os, logging, json, httpx, asyncio

log = logging.getLogger(__name__)

def _env(k, d=None):
    v = os.environ.get(k)
    return v if v not in (None, "") else d

class XpBridgeKvInit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.url = _env("UPSTASH_REDIS_REST_URL")
        self.tok = _env("UPSTASH_REDIS_REST_TOKEN")

    async def cog_load(self):
        if not (self.url and self.tok):
            log.warning("[xp-kv-init] Upstash env missing; skip")
            return
        try:
            await self._ensure_key("xpbridge:last_total_xp", "0")
            # don't touch xp:store or ladder keys; only watermark to satisfy bridge
            log.info("[xp-kv-init] ensured xpbridge:last_total_xp exists")
        except Exception as e:
            log.warning("[xp-kv-init] ensure failed: %r", e)

    async def _ensure_key(self, key: str, default_val: str):
        async with httpx.AsyncClient(timeout=10.0) as x:
            # EXISTS
            r = await x.post(self.url, headers={"Authorization": f"Bearer {self.tok}", "Content-Type": "application/json"}, json=["EXISTS", key])
            r.raise_for_status()
            ex = r.json().get("result", 0)
            if ex == 1:
                return
            # SETNX
            r2 = await x.post(self.url, headers={"Authorization": f"Bearer {self.tok}", "Content-Type": "application/json"}, json=["SETNX", key, str(default_val)])
            r2.raise_for_status()

async def setup(bot):
    await bot.add_cog(XpBridgeKvInit(bot))