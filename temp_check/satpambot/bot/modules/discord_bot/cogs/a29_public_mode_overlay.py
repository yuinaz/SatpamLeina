from __future__ import annotations

import logging
from satpambot.config.local_cfg import cfg_bool
log = logging.getLogger(__name__)
try:
    from satpambot.bot.modules.discord_bot.cogs import public_chat_gate as pcg
    if cfg_bool("PUBLIC_MODE_ENABLE", False):
        if getattr(pcg, "LOCK_ON_BOOT", None) is True:
            pcg.LOCK_ON_BOOT = False
            log.info("[public_mode_overlay] LOCK_ON_BOOT -> False (public mode)")
    mreq = cfg_bool("CHAT_MENTIONS_ONLY", True)
    if getattr(pcg, "MENTION_REQUIRED_WHEN_ALLOWED", None) != mreq:
        pcg.MENTION_REQUIRED_WHEN_ALLOWED = mreq
        log.info("[public_mode_overlay] MENTION_REQUIRED_WHEN_ALLOWED -> %s", mreq)
except Exception as e:
    log.warning("[public_mode_overlay] failed: %s", e)