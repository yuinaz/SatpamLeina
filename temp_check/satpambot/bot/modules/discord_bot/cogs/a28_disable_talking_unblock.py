from __future__ import annotations

import logging
from satpambot.config.local_cfg import cfg_bool
log = logging.getLogger(__name__)
try:
    if cfg_bool("PUBLIC_MODE_ENABLE", False):
        from satpambot.bot.modules.discord_bot.cogs import a00_disable_talking_modules as dtm
        blocked = getattr(dtm, "BLOCK_PREFIXES", [])
        keep = []
        for p in blocked:
            if "chat_neurolite" in p or "public_send_router" in p or "diag_public" in p:
                log.info("[disable_talking_unblock] allow %s", p)
                continue
            keep.append(p)
        dtm.BLOCK_PREFIXES = keep
except Exception as e:
    log.warning("[disable_talking_unblock] failed: %s", e)