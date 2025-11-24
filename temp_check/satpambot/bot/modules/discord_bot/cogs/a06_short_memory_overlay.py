
from discord.ext import commands
"""a06_short_memory_overlay.py (v8.2)"""
import time, os, logging
from collections import deque, defaultdict

log = logging.getLogger(__name__)

class ShortMemoryStore:
    def __init__(self, limit=3, ttl=900):
        self.limit = int(os.getenv("SHORT_MEM_LIMIT", limit))
        self.ttl = int(os.getenv("SHORT_MEM_TTL_SEC", ttl))
        self._buf = defaultdict(lambda: deque(maxlen=self.limit))
    def add(self, user_id: int, content: str):
        now = time.time(); self._buf[user_id].append((now, content))
    def get(self, user_id: int):
        now = time.time(); items = list(self._buf[user_id])
        fresh = [c for (t,c) in items if (now - t) <= self.ttl]
        if len(fresh) < len(items):
            self._buf[user_id].clear()
            for c in fresh: self._buf[user_id].append((now, c))
        return fresh[-self.limit:]

class ShortMemoryOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot; self.store = ShortMemoryStore()
    @commands.Cog.listener("on_message")
    async def _on_message(self, message):
        if getattr(message.author, "bot", False): return
        content = (message.content or "").strip()
        if not content: return
        try: self.store.add(message.author.id, content)
        except Exception as e: log.warning("[short-mem] add failed: %r", e)
    def get_short_context(self, user_id: int): return self.store.get(user_id)
async def setup(bot): await bot.add_cog(ShortMemoryOverlay(bot))
def setup(bot):
    try:
        import asyncio
        if asyncio.get_event_loop().is_running():
            return asyncio.create_task(bot.add_cog(ShortMemoryOverlay(bot)))
    except Exception: pass
    return bot.add_cog(ShortMemoryOverlay(bot))