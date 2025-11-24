from __future__ import annotations

import logging
from satpambot.config.local_cfg import cfg_int
log = logging.getLogger(__name__)
try:
    mod = __import__("satpambot.bot.modules.discord_bot.cogs.live_metrics_push", fromlist=["*"])
    period = int(cfg_int("PERIODIC_STATUS_SEC", getattr(mod, "PERIOD_SEC", 300)) or getattr(mod, "PERIOD_SEC", 300))
    if hasattr(mod, "PERIOD_SEC"): mod.PERIOD_SEC = max(600, period)
    setattr(mod, "EDIT_ONLY", True)
    log.info("[periodic_status_throttle] period=%ss edit_only=True", getattr(mod, "PERIOD_SEC", period))
except Exception as e:
    log.warning("[periodic_status_throttle] failed: %s", e)