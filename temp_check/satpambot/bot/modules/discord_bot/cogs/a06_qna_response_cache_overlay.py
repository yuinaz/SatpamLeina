
from discord.ext import commands
"""a06_qna_response_cache_overlay.py (v8.2)"""
import os, json, hashlib, logging
import httpx

log = logging.getLogger(__name__)

class UpstashClient:
    def __init__(self):
        self.url = os.getenv("UPSTASH_REDIS_REST_URL")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        self.enabled = bool(self.url and self.token)
        self.ttl = int(os.getenv("QNA_CACHE_TTL_SEC", "300"))
        self._client = httpx.AsyncClient(timeout=8.0)
    async def get(self, key):
        if not self.enabled: return None
        try:
            r = await self._client.get(f"{self.url}/get/{key}", headers={"Authorization": f"Bearer {self.token}"})
            if r.status_code==200:
                return r.json().get("result")
        except Exception as e: log.debug("[qna-cache] get failed: %r", e)
        return None
    async def setex(self, key, ttl, value):
        if not self.enabled: return False
        try:
            r = await self._client.get(f"{self.url}/setex/{key}/{ttl}/{value}", headers={"Authorization": f"Bearer {self.token}"})
            return r.status_code==200
        except Exception as e: log.debug("[qna-cache] setex failed: %r", e)
        return False

class QnAResponseCache(commands.Cog):
    import hashlib
    def __init__(self, bot): self.bot = bot; self.cli = UpstashClient()
    def _key(self, q: str):
        h = hashlib.sha1(q.encode("utf-8")).hexdigest()
        return f"qna:cache:{h}"
    async def try_get_cached(self, question: str):
        return await self.cli.get(self._key(question))
    async def cache_answer(self, question: str, answer: str):
        await self.cli.setex(self._key(question), self.cli.ttl, answer)
async def setup(bot): await bot.add_cog(QnAResponseCache(bot))
def setup(bot):
    try:
        import asyncio
        if asyncio.get_event_loop().is_running():
            return asyncio.create_task(bot.add_cog(QnAResponseCache(bot)))
    except Exception: pass
    return bot.add_cog(QnAResponseCache(bot))