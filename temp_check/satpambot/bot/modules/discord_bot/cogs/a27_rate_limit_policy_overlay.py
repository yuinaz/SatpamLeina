from __future__ import annotations

import logging
from satpambot.config.local_cfg import cfg_int

log = logging.getLogger(__name__)

try:
    from satpambot.bot.modules.discord_bot.cogs import rate_limit_guard as rlg
    rlg.REPLY_COOLDOWN_SEC = int(cfg_int("PUBLIC_REPLY_COOLDOWN_SEC", getattr(rlg, "REPLY_COOLDOWN_SEC", 8)) or 8)
    rlg.MAX_CONCURRENT = int(cfg_int("PUBLIC_MAX_CONCURRENT", getattr(rlg, "MAX_CONCURRENT", 2)) or 2)
    rlg.BURST = int(cfg_int("PUBLIC_BURST", getattr(rlg, "BURST", 3)) or 3)
    log.info("[rate_limit_policy] cooldown=%ss max_conc=%s burst=%s", rlg.REPLY_COOLDOWN_SEC, rlg.MAX_CONCURRENT, rlg.BURST)
except Exception as e:
    log.warning("[rate_limit_policy] overlay failed: %s", e)