from __future__ import annotations

from discord.ext import commands

import logging
import re

LOGGER = logging.getLogger(__name__)

TARGET_CHANNEL_IDS = { 1400375184048787566, 1425400701982478408 }

LOG_PATTERNS = [
    re.compile(r"^(INFO|WARNING|ERROR)\:"),
    re.compile(r"loaded satpambot", re.IGNORECASE),
    re.compile(r"smoke_cogs\.py|smoke_lint_thread_guard\.py", re.IGNORECASE),
]

MAX_LEN = 2000
MAX_LINES = 30

def is_spam(content: str) -> bool:
    if not content:
        return False
    if len(content) > MAX_LEN or content.count("\n") > MAX_LINES:
        return True
    return any(p.search(content) for p in LOG_PATTERNS)

class SpamAutoDeleteGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if message.channel.id not in TARGET_CHANNEL_IDS:
            return
        if is_spam(message.content or ""):
            try:
                await message.delete()
            except Exception as e:
                LOGGER.debug("Failed to delete spam: %s", e)
async def setup(bot):
    await bot.add_cog(SpamAutoDeleteGuard(bot))