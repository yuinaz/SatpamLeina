from __future__ import annotations
import asyncio, logging, inspect
from discord.ext import commands
log = logging.getLogger(__name__)

def _wrap(bot, name):
    orig = getattr(bot, name, None)
    if not orig or getattr(orig, "_guard_wrapped", False): return
    async def _ensure(*a, **k):
        r = orig(*a, **k)
        if inspect.isawaitable(r): return await r
        return r
    def wrapper(*a, **k):
        try: loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        t = loop.create_task(_ensure(*a, **k))
        class _F: 
            def __await__(self): return t.__await__()
        return _F()
    wrapper._guard_wrapped = True  # type: ignore
    setattr(bot, name, wrapper)

class CogOpsGuard(commands.Cog):
    def __init__(self, bot): 
        _wrap(bot, "add_cog"); _wrap(bot, "remove_cog"); log.info("[cog-guard] wrapped add/remove_cog")

async def setup(bot: commands.Bot):
    await bot.add_cog(CogOpsGuard(bot))
