from discord.ext import commands
import inspect, logging, asyncio

log = logging.getLogger(__name__)

async def _maybe_add_cog(bot, cog):
    add = getattr(bot, "add_cog", None)
    if not add:
        return
    try:
        res = add(cog)
        if inspect.isawaitable(res):
            await res
    except Exception as e:
        log.exception("failed to add cog %s: %s", type(cog).__name__, e)

import logging

log = logging.getLogger(__name__)

class PublicChatGate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("PublicChatGate: add_check registered.")
async def setup(bot):
    if bot.get_cog("PublicChatGate"):
        return
    await _maybe_add_cog(bot, PublicChatGate(bot))