from __future__ import annotations
import re, logging, asyncio
from discord.ext import commands

log = logging.getLogger(__name__)

def _is_int_str(s):
    return isinstance(s, (str, bytes)) and re.fullmatch(r"-?\d+", s.decode() if isinstance(s, bytes) else s) is not None

class SeniorTotalSanitizeOnce(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_str
        self.total_key = cfg_str("XP_SENIOR_KEY","xp:bot:senior_total")
        self._done = False

    async def _run_once(self):
        if self._done:
            return
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
            kv = PinnedJSONKV(self.bot)
            us = UpstashClient()
            try:
                cur = await us.get_raw(self.total_key)
            except Exception as e:
                log.debug("[total-sanitize] GET failed: %r", e)
                cur = None
            if _is_int_str(cur):
                self._done = True
                return
            m = await kv.get_map()
            pinned = m.get(self.total_key)
            if _is_int_str(pinned) or isinstance(pinned, int):
                val = int(pinned) if not _is_int_str(pinned) else int(pinned)
            else:
                val = 0
            try:
                await us.set(self.total_key, str(val))
                log.warning("[total-sanitize] fixed %s -> %s", self.total_key, val)
            except Exception as e:
                log.debug("[total-sanitize] SET failed: %r", e)
            self._done = True
        except Exception as e:
            log.debug("[total-sanitize] skip: %r", e)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        asyncio.create_task(self._run_once())

async def setup(bot):
    await bot.add_cog(SeniorTotalSanitizeOnce(bot))
