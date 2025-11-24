from __future__ import annotations
from discord.ext import commands

# a00_xp_kv_selfheal_overlay.py
import os, json, asyncio, logging
from typing import Optional
try:
    import httpx
except Exception:
    httpx = None

log = logging.getLogger(__name__)
UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
KEY = "xp:bot:senior_total"

class XpKvSelfHeal(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        try:
            asyncio.create_task(self._self_heal())
        except Exception:
            pass

    async def _self_heal(self) -> None:
        if not (UPSTASH_URL and UPSTASH_TOKEN and httpx):
            return
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                hdr = {"Authorization": f"Bearer {UPSTASH_TOKEN}"}
                r = await client.get(f"{UPSTASH_URL}/get/{KEY}", headers=hdr)
                r.raise_for_status()
                data = r.json()
                raw = (data or {}).get("result", None)
                if raw is None:
                    return
                coerced: Optional[int] = None
                try:
                    coerced = int(raw)
                except Exception:
                    try:
                        obj = json.loads(raw) if isinstance(raw, str) else raw
                        if isinstance(obj, dict) and "senior_total_xp" in obj:
                            coerced = int(obj["senior_total_xp"])
                            log.warning("[xp-selfheal] Found legacy JSON for %s: %r", KEY, obj)
                    except Exception:
                        pass
                if coerced is None:
                    return
                if str(raw) != str(coerced):
                    wr = await client.post(f"{UPSTASH_URL}/set/{KEY}/{coerced}", headers=hdr)
                    wr.raise_for_status()
                    log.info("[xp-selfheal] Normalized %s to %d", KEY, coerced)
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(XpKvSelfHeal(bot))
    def cog_unload(self):
        pass
