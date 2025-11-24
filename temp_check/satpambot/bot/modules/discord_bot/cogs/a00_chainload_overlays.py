# -*- coding: utf-8 -*-
import os, importlib, asyncio, logging
log=logging.getLogger(__name__)

MODULES = [
    # --- smoke helpers ---
    "satpambot.bot.modules.discord_bot.cogs.a97_smoke_autodetect_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a96_smoke_thread_daemonizer_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a98_smoke_guard_overlay",
    # --- hardening ---
    "satpambot.bot.modules.discord_bot.cogs.a06_embed_scribe_post_shim_v2",
    "satpambot.bot.modules.discord_bot.cogs.a00_progress_embed_safeawait_bootstrap",
    "satpambot.bot.modules.discord_bot.cogs.a10_progress_embed_guard_overlay",
    # --- rest (biarkan sama; extra via EXTRA_COGS) ---
]

def _expand_env_list(key: str):
    raw=os.getenv(key,"").strip()
    return [s.strip() for s in raw.split(",") if s.strip()] if raw else []

def _dedup_keep_order(seq):
    seen=set(); out=[]
    for x in seq:
        if x not in seen:
            out.append(x); seen.add(x)
    return out

async def _maybe_setup(mod, bot):
    setup=getattr(mod,"setup",None)
    if setup:
        try:
            if asyncio.iscoroutinefunction(setup):
                await setup(bot)
            else:
                res=setup(bot)
                if asyncio.iscoroutine(res): await res
        except Exception as e:
            log.warning("[chain] setup failed for %s: %r", getattr(mod,"__name__",mod), e)

async def _run(bot):
    skip=set(_expand_env_list("CHAIN_SKIP"))
    extra=_expand_env_list("EXTRA_COGS")
    # gabungkan MODULES + EXTRA_COGS (urutan dipertahankan)
    mods=[m for m in MODULES if m not in skip]+[m for m in extra if m not in skip]
    mods=_dedup_keep_order([m for m in mods if not m.startswith("modules.discord_bot.cogs.")])
    for name in mods:
        try:
            mod=importlib.import_module(name)
        except Exception as e:
            log.warning("[chain] import failed %s: %r", name, e); continue
        await _maybe_setup(mod, bot)
        log.info("[chain] loaded %s", name)
async def setup(bot): await _run(bot)
def setup(bot):
    try:
        loop=asyncio.get_event_loop()
        if loop and loop.is_running():
            return loop.create_task(_run(bot))
    except Exception: pass
    return asyncio.run(_run(bot))
