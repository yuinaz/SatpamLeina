
from __future__ import annotations
import logging, asyncio
from discord.ext import commands
from satpambot.bot.modules.discord_bot.helpers.qna_quota_router import monkey_patch_failover_quota
from satpambot.bot.modules.discord_bot.helpers.task_tools import create_task_any

log = logging.getLogger(__name__)

class QnaProviderAutoFailoverLocalOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _late(self):
        await asyncio.sleep(0)
        try:
            await monkey_patch_failover_quota()
            log.info("[qna-local-failover] monkey patch active")
        except Exception as e:
            log.exception("[qna-local-failover] patch failed: %r", e)

async def setup(bot):
    cog = QnaProviderAutoFailoverLocalOverlay(bot)
    await bot.add_cog(cog)
    create_task_any(bot, cog._late())
