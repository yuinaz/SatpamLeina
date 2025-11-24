from __future__ import annotations

import logging
from satpambot.config.local_cfg import cfg_bool
log = logging.getLogger(__name__)
try:
    from satpambot.bot.modules.discord_bot.cogs import public_chat_gate as pcg
    approved = cfg_bool("INTERVIEW_APPROVED", False)
    want_public = cfg_bool("PUBLIC_MODE_ENABLE", False)
    if want_public and not approved:
        if getattr(pcg, "LOCK_ON_BOOT", None) is not None:
            pcg.LOCK_ON_BOOT = True
        log.warning("[interview_gate] PUBLIC_MODE_ENABLE requested but blocked (INTERVIEW_APPROVED=false).")
except Exception as e:
    log.warning("[interview_gate] failed: %s", e)