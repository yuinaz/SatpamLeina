from discord.ext import commands

import asyncio
import logging

log = logging.getLogger(__name__.split('.')[-1])

# This overlay tries to upsert the pinned XP snapshot to a desired total (default 1500).
# It is defensive: if helper APIs are missing, it will no-op and log a hint.
#
# Reads config from runtime cfg/local.json:
#   XP_FORCE_TOTAL (int)  -> target total XP (default 1500)
#
# It piggybacks the existing memory_upsert helper used by your pinned backend.

async def _run(bot):
    await bot.wait_until_ready()

    # get target total
    try:
        from satpambot.config.runtime import cfg
        target = int(cfg("XP_FORCE_TOTAL", 1500) or 1500)
    except Exception:
        target = 1500
    log.info("[xp_force_seed] requested total=%s", target)

    # Try to use the helper your stack already logs:
    # "memory_upsert: pinned 'XP: Miner Memory' snapshot ..."
    try:
        from satpambot.bot.modules.discord_bot.helpers.memory_upsert import upsert_pinned_memory
    except Exception as e:
        log.warning("[xp_force_seed] memory_upsert helper not found (%s) — skip", e)
        return

    # Prepare a conservative payload—wrappers in your stack should route to the right thread.
    payload = {
        "title": "XP: Miner Memory",
        # Keep it simple: your backend parser only needs `total=...` present.
        "content": f"total={target}\n",
        # Optional metadata if your wrappers want them; ignored otherwise.
        "meta": {"source": "xp_force_seed_overlay"}
    }
    try:
        ok = await upsert_pinned_memory(bot, payload)
        log.info("[xp_force_seed] upsert_pinned_memory result=%s", ok)
    except TypeError as e:
        # Some older wrappers required explicit guild/channel/title; log hint and continue harmlessly.
        log.warning("[xp_force_seed] helper signature mismatch (%s). "
                    "If needed, set the correct PREFERRED_THREAD_ID via your progress overlay.", e)
    except Exception as e:
        log.error("[xp_force_seed] failed to upsert XP snapshot: %s", e)

async def setup(bot):
    # schedule background task, no side effects on import
    asyncio.create_task(_run(bot))