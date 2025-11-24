from __future__ import annotations

import logging
from satpambot.config.local_cfg import cfg_int

log = logging.getLogger(__name__)

def _patch_budget(mod_name: str, per_key: str, total_key: str, skip_key: str):
    try:
        mod = __import__(mod_name, fromlist=["*"])
        per_ch = int(cfg_int(per_key, getattr(mod, "PER_CHANNEL_LIMIT", 100)) or getattr(mod, "PER_CHANNEL_LIMIT", 100))
        total  = int(cfg_int(total_key, getattr(mod, "TOTAL_BUDGET", 900)) or getattr(mod, "TOTAL_BUDGET", 900))
        skip   = int(cfg_int(skip_key, getattr(mod, "SKIP_RECENT", 8)) or getattr(mod, "SKIP_RECENT", 8))
        if hasattr(mod, "PER_CHANNEL_LIMIT"):
            mod.PER_CHANNEL_LIMIT = per_ch
        if hasattr(mod, "TOTAL_BUDGET"):
            mod.TOTAL_BUDGET = total
        if hasattr(mod, "SKIP_RECENT"):
            mod.SKIP_RECENT = skip
        log.info("[miner_tuning] %s: per_ch=%s total=%s skip=%s", mod_name, per_ch, total, skip)
    except Exception as e:
        log.debug("[miner_tuning] %s failed: %s", mod_name, e)

try:
    _patch_budget("satpambot.bot.modules.discord_bot.cogs.slang_hourly_miner",
                  "SLANG_PER_CHANNEL", "SLANG_TOTAL_BUDGET", "SLANG_SKIP")
    _patch_budget("satpambot.bot.modules.discord_bot.cogs.phish_text_hourly_miner",
                  "PHISH_PER_CHANNEL", "PHISH_TOTAL_BUDGET", "PHISH_SKIP")
except Exception as e:
    log.warning("[miner_tuning] overlay failed: %s", e)