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

import logging, inspect

log = logging.getLogger(__name__)

class PublicSendRouter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_text(self, channel, content=None, **kwargs):
        try:
            if content is None and not kwargs:
                return
            res = channel.send(content, **kwargs)
            if inspect.isawaitable(res):
                return await res
            return res
        except Exception as e:
            log.exception("PublicSendRouter.send_text failed: %s", e)
async def setup(bot):
    if bot.get_cog("PublicSendRouter"):
        return
    await _maybe_add_cog(bot, PublicSendRouter(bot))