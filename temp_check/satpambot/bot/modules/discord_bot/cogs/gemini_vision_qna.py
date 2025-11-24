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

def build_vision_messages(prompt: str, image_url: str | None):
    if not image_url:
        return [{"role": "user", "content": (prompt or "Jelaskan secara ringkas.").strip()}]
    return [{"role": "user", "content": [{"type":"text","text": (prompt or "Jelaskan gambar ini.").strip()}, {"type":"image_url","image_url":{"url": image_url}}]}]

class GeminiVisionQnA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.info("GeminiVisionQnA: ready")
async def setup(bot):
    if bot.get_cog("GeminiVisionQnA"):
        return
    await _maybe_add_cog(bot, GeminiVisionQnA(bot))