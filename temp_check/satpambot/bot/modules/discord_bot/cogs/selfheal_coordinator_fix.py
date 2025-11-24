from __future__ import annotations

import logging
log = logging.getLogger(__name__)

def _try_import():
    mods = [
        "satpambot.bot.modules.discord_bot.cogs.selfheal_router",
        "satpambot.bot.modules.discord_bot.cogs.selfheal_thread_router",
    ]
    got = []
    for m in mods:
        try:
            got.append(__import__(m, fromlist=["*"]))
        except Exception as e:
            log.debug("[selfheal_coordinator_fix] import %s failed: %s", m, e)
    return got

try:
    _ = _try_import()
    log.info("[selfheal_coordinator_fix] selfheal router modules import checked (quiet).")
except Exception as e:
    log.warning("[selfheal_coordinator_fix] failed: %s", e)