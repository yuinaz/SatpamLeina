from __future__ import annotations

from discord.ext import commands

import logging

log = logging.getLogger(__name__)

class LearningPromotionGate(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        log.info("[learning_promotion_gate] defensive mode enabled (no-op keeper; stable local run)")
async def setup(bot: commands.Bot):
    await bot.add_cog(LearningPromotionGate(bot))