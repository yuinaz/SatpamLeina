
from __future__ import annotations
import logging
from discord.ext import commands

log = logging.getLogger(__name__)

class PreferUpstashBootstrapFixOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _safe_fetch(self):
        try:
            from satpambot.bot.modules.discord_bot.cogs.a00_prefer_upstash_bootstrap import _fetch_state_from_upstash
            return await _fetch_state_from_upstash()
        except Exception as e:
            log.warning("[prefer-upstash-fix] fetch failed: %r", e)
            return None

    @commands.Cog.listener()
    async def on_ready(self):
        # Only ensure keys when Upstash fetch succeeded AND senior_total is valid
        st = await self._safe_fetch()
        if not st:
            log.info("[prefer-upstash-fix] skip ensure (no state)")
            return
        try:
            senior = st.get("senior_total")
            if not isinstance(senior, (int, float)) or int(senior) <= 0:
                log.info("[prefer-upstash-fix] skip ensure (invalid senior_total=%r)", senior)
                return
        except Exception:
            return
        # Otherwise: let original bootstrap handle normal flow (it will mirror on demand)
        log.info("[prefer-upstash-fix] state looks valid; no-op overlay")

async def setup(bot):
    await bot.add_cog(PreferUpstashBootstrapFixOverlay(bot))
