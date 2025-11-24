
from discord.ext import commands
"""
a06_xp_event_normalizer_overlay.py
- Listens to xp events with variable signatures and writes to Upstash if present.
- Events: 'xp_add', 'xp.award', 'satpam_xp'
- Handles Member/User/int id; kwargs reason optional.
"""
import logging, os, httpx, asyncio

log = logging.getLogger(__name__)

class UpstashMini:
    def __init__(self):
        self.url = os.getenv('UPSTASH_REST_URL') or os.getenv('UPSTASH_REDIS_REST_URL')
        self.token = os.getenv('UPSTASH_REST_TOKEN') or os.getenv('UPSTASH_REDIS_REST_TOKEN')
        self.enabled = bool(self.url and self.token)
    async def incrby(self, key, amt):
        if not self.enabled: return False
        try:
            async with httpx.AsyncClient(timeout=6.0) as cli:
                r = await cli.get(f"{self.url}/incrby/{key}/{int(amt)}",
                                  headers={"Authorization": f"Bearer {self.token}"})
                return r.status_code == 200
        except Exception as e:
            log.debug("[xp-norm] upstash failed: %r", e); return False

def _user_id(u):
    try:
        return int(getattr(u, "id", u))
    except Exception:
        return None

class XPNormalizer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.us = UpstashMini()

    async def _handle(self, *args, **kwargs):
        if not args: return
        uid = _user_id(args[0])
        amt = None
        if len(args) >= 2:
            try: amt = int(args[1])
            except Exception: amt = 0
        if uid is None or amt is None:
            return
        key = f"xp:store:{uid}"
        await self.us.incrby(key, amt)

    @commands.Cog.listener("on_satpam_xp")
    async def on_satpam_xp(self, *args, **kwargs):
        await self._handle(*args, **kwargs)

    @commands.Cog.listener("on_xp_add")
    async def on_xp_add(self, *args, **kwargs):
        await self._handle(*args, **kwargs)

    @commands.Cog.listener("on_xp_award")
    async def on_xp_award(self, *args, **kwargs):
        await self._handle(*args, **kwargs)
async def setup(bot):
    await bot.add_cog(XPNormalizer(bot))

def setup(bot):
    try:
        import asyncio
        if asyncio.get_event_loop().is_running():
            return asyncio.create_task(bot.add_cog(XPNormalizer(bot)))
    except Exception:
        pass
    return bot.add_cog(XPNormalizer(bot))