from __future__ import annotations

import logging, random
from satpambot.config.local_cfg import cfg_int

log = logging.getLogger(__name__)

def _apply_period(mod_name: str, attr_period: str, default_sec: int, jitter: int, start_attr: str = None, default_delay: int = None):
    try:
        mod = __import__(mod_name, fromlist=["*"])
        period = int(cfg_int(attr_period, default_sec) or default_sec)
        if jitter:
            period += random.randint(-abs(jitter), abs(jitter))
            if period < 60:
                period = 60
        if hasattr(mod, "PERIOD_SEC"):
            mod.PERIOD_SEC = period
        if start_attr and default_delay is not None and hasattr(mod, "START_DELAY_SEC"):
            delay = int(cfg_int(start_attr, default_delay) or default_delay)
            setattr(mod, "START_DELAY_SEC", delay)
        log.info("[shadow_cadence] %s: every=%ss start=%ss", mod_name, period, getattr(mod, "START_DELAY_SEC", "?"))
    except Exception as e:
        log.debug("[shadow_cadence] %s failed: %s", mod_name, e)

try:
    _apply_period("satpambot.bot.modules.discord_bot.cogs.phish_text_hourly_miner",
                  "SLANG_PHISH_PERIOD_SEC", 300, 30, "SLANG_PHISH_START_SEC", 35)
    _apply_period("satpambot.bot.modules.discord_bot.cogs.slang_hourly_miner",
                  "SLANG_TEXT_PERIOD_SEC", 300, 30, "SLANG_TEXT_START_SEC", 40)
    _apply_period("satpambot.bot.modules.discord_bot.cogs.text_activity_hourly_miner",
                  "TEXT_ACTIVITY_PERIOD_SEC", 300, 30, "TEXT_ACTIVITY_START_SEC", 30)
except Exception as e:
    log.warning("[shadow_cadence] overlay failed: %s", e)