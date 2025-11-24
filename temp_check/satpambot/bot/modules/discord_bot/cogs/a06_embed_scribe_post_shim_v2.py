# -*- coding: utf-8 -*-
"""
a06_embed_scribe_post_shim_v2 (fixed)
- Eager inject + on_ready re-inject
- **FIX**: no recursive setup(); use setup_async()
"""
from discord.ext import commands
import importlib, inspect, logging, asyncio

log = logging.getLogger(__name__)

def _inject():
    try:
        mod = importlib.import_module("satpambot.bot.utils.embed_scribe")
    except Exception as e:
        log.warning("[post_shim_v2] embed_scribe module missing: %r", e); return False
    ES = getattr(mod, "EmbedScribe", None)
    if ES is None:
        class EmbedScribe(object):
            def __init__(self, bot): self.bot=bot
            async def upsert(self, channel, key, embed, pin=False):
                return None
        mod.EmbedScribe = EmbedScribe
        log.info("[post_shim_v2] provided fallback EmbedScribe with async upsert()")
        return True
    if not hasattr(ES, "upsert"):
        async def upsert(self, channel, key, embed, pin=False): return None
        setattr(ES, "upsert", upsert)
        log.info("[post_shim_v2] added missing upsert() to EmbedScribe")
        return True
    up = getattr(ES, "upsert")
    if not inspect.iscoroutinefunction(up):
        async def _up(self, *a, **k):
            res = up(self, *a, **k)
            if inspect.isawaitable(res): return await res
            return res
        setattr(ES, "upsert", _up)
        log.info("[post_shim_v2] wrapped non-async upsert() with async shim")
    return True

# eager
try: _inject()
except Exception as _e: log.debug("[post_shim_v2] eager inject failed: %r", _e)

class PostShimV2(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @commands.Cog.listener()
    async def on_ready(self): _inject()

async def setup_async(bot): await bot.add_cog(PostShimV2(bot))

def setup(bot):
    try:
        loop = asyncio.get_event_loop()
        if loop and loop.is_running():
            return loop.create_task(setup_async(bot))
    except Exception:
        pass
    return asyncio.run(setup_async(bot))