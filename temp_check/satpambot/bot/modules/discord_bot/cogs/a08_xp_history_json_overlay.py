from discord.ext import commands

import logging

log = logging.getLogger(__name__)

LOOKBACK_HOURS = 24 * 7   # 7 days
AUTHOR_COOLDOWN_SEC = 6

class XPHistoryJsonOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    log.info("[xp_history_json_overlay] set LOOKBACK_HOURS = %d", LOOKBACK_HOURS)
    log.info("[xp_history_json_overlay] set AUTHOR_COOLDOWN_SEC = %d", AUTHOR_COOLDOWN_SEC)
    await bot.add_cog(XPHistoryJsonOverlay(bot))