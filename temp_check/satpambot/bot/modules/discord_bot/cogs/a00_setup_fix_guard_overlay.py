# -*- coding: utf-8 -*-
import importlib, inspect, asyncio, logging, types
log=logging.getLogger(__name__)
TARGETS=[
"satpambot.bot.modules.discord_bot.cogs.a00_governor_gate_neurosama_overlay",
"satpambot.bot.modules.discord_bot.cogs.a00_qna_allowlist_bridge_overlay",
"satpambot.bot.modules.discord_bot.cogs.a01_interview_thread_overlay",
"satpambot.bot.modules.discord_bot.cogs.a02_status_card_embed_overlay",
"satpambot.bot.modules.discord_bot.cogs.a03_cleanup_tools_overlay",
"satpambot.bot.modules.discord_bot.cogs.a06_persona_unified_provider_overlay",
"satpambot.bot.modules.discord_bot.cogs.a06_embed_scribe_post_shim_v3",
]
def _patch_module(mod: types.ModuleType)->bool:
    if hasattr(mod,"setup_async") and inspect.iscoroutinefunction(getattr(mod,"setup_async")):
        return False
    if hasattr(mod,"setup") and inspect.iscoroutinefunction(getattr(mod,"setup")):
        orig=getattr(mod,"setup")
        setattr(mod,"setup_async_orig",orig)
        async def setup_async(bot): return await orig(bot)
        def setup(bot):
            try:
                loop=asyncio.get_event_loop()
                if loop and loop.is_running(): return loop.create_task(setup_async(bot))
            except Exception: pass
            return asyncio.run(setup_async(bot))
        setattr(mod,"setup_async",setup_async); setattr(mod,"setup",setup); return True
    orig_async=getattr(mod,"setup_async_orig",None) or getattr(mod,"setup_async",None)
    if orig_async and inspect.iscoroutinefunction(orig_async):
        def setup(bot):
            try:
                loop=asyncio.get_event_loop()
                if loop and loop.is_running(): return loop.create_task(orig_async(bot))
            except Exception: pass
            return asyncio.run(orig_async(bot))
        setattr(mod,"setup",setup); return True
    return False
def _apply():
    c=0
    for name in TARGETS:
        try: mod=importlib.import_module(name)
        except Exception as e: log.debug("[setup-fix] import skip %s: %r",name,e); continue
        try:
            if _patch_module(mod): c+=1
        except Exception as e:
            log.warning("[setup-fix] patch fail %s: %r",name,e)
    if c: log.info("[setup-fix] patched %d modules",c)
try: _apply()
except Exception as e: log.debug("[setup-fix] apply fail: %r",e)
async def setup(bot): return None
