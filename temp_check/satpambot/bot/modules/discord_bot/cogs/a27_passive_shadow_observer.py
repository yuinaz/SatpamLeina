
from __future__ import annotations
import asyncio, logging
from typing import Optional, Tuple
from discord.ext import commands, tasks
log = logging.getLogger(__name__)
async def _upstash_get_async(key: str) -> Tuple[Optional[str], Optional[int]]:
    try:
        from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
        val = await UpstashClient().get_raw(key)
        return (str(val) if val is not None else None, 200)
    except Exception as e:
        log.debug("[shadow-observer] upstash get %s failed: %r", key, e)
        return (None, None)
class PassiveShadowObserver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.backfill_loop.start()
    def cog_unload(self):
        try: self.backfill_loop.cancel()
        except Exception: pass
    @tasks.loop(minutes=3.0)
    async def backfill_loop(self):
        try:
            await self.bot.wait_until_ready()
            key = "shadow:last_text"
            last_txt,_ = await _upstash_get_async(key)
            if last_txt is None: return
        except Exception as e:
            log.info("[shadow-observer] loop soft-fail: %r", e)
    @backfill_loop.before_loop
    async def _before(self): await self.bot.wait_until_ready()
async def setup(bot): await bot.add_cog(PassiveShadowObserver(bot))
