# -*- coding: utf-8 -*-
"""
a10_progress_embed_guard_overlay
Render Free guard untuk dua titik rawan:
1) EmbedScribe.upsert → dipastikan coroutine-friendly (maybe-await).
2) progress_embed_solo.update_embed → dipastikan pakai maybe-await juga.

Idempotent; aman dipanggil berulang.
"""
from discord.ext import commands
import importlib, inspect, logging, asyncio

log=logging.getLogger(__name__)

def _wrap_upsert():
    try:
        mod=importlib.import_module("satpambot.bot.utils.embed_scribe")
        ES=getattr(mod,"EmbedScribe",None)
        if ES is None: return False
        up=getattr(ES,"upsert",None)
        if up is None:
            async def upsert(self,*a,**k): return None
            setattr(ES,"upsert", upsert)
            log.info("[progress-guard] add missing EmbedScribe.upsert()")
            return True
        if not inspect.iscoroutinefunction(up):
            async def _up(self,*a,**k):
                res=up(self,*a,**k)
                if inspect.isawaitable(res): return await res
                return res
            setattr(ES,"upsert", _up)
            log.info("[progress-guard] wrap non-async upsert() with async shim")
            return True
        return True
    except Exception as e:
        log.warning("[progress-guard] upsert wrap fail: %r", e); return False

def _wrap_update_embed():
    try:
        mod=importlib.import_module("satpambot.bot.modules.discord_bot.cogs.progress_embed_solo")
    except Exception as e:
        log.debug("[progress-guard] no progress_embed_solo: %r", e); return False
    fn=getattr(mod,"update_embed",None)
    if fn is None: 
        log.debug("[progress-guard] update_embed missing"); return False
    if getattr(fn,"__wrapped_by_guard__",False): 
        return True
    async def _maybe_await(v):
        if inspect.isawaitable(v): return await v
        return v
    async def wrapped(*a,**k):
        try:
            res=fn(*a,**k)
            return await _maybe_await(res)
        except Exception as e:
            log.warning("[progress-guard] update error (wrapped): %r", e)
            return None
    wrapped.__wrapped_by_guard__=True
    setattr(mod,"update_embed", wrapped)
    log.info("[progress-guard] wrapped progress_embed_solo.update_embed")
    return True

def _apply():
    ok1=_wrap_upsert()
    ok2=_wrap_update_embed()
    return ok1 or ok2

class Guard(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @commands.Cog.listener()
    async def on_ready(self): _apply()

async def setup_async(bot): 
    await bot.add_cog(Guard(bot)); _apply()

def setup(bot):
    try:
        loop=asyncio.get_event_loop()
        if loop and loop.is_running(): 
            return loop.create_task(setup_async(bot))
    except Exception: 
        pass
    return asyncio.run(setup_async(bot))