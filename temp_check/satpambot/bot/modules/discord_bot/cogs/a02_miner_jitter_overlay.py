from __future__ import annotations

import logging, random, importlib
log = logging.getLogger(__name__)

TARGETS = [
    ("satpambot.bot.modules.discord_bot.cogs.text_activity_hourly_miner", 30, 300, "TEXT"),
    ("satpambot.bot.modules.discord_bot.cogs.phish_text_hourly_miner",     35, 300, "PHISH"),
    ("satpambot.bot.modules.discord_bot.cogs.slang_hourly_miner",          40, 300, "SLANG"),
]

def _apply_jitter(mod_name: str, base_delay: int, base_period: int, tag: str):
    try:
        m = importlib.import_module(mod_name)
    except Exception as e:
        log.warning("[miner_jitter] import %s failed: %s", mod_name, e)
        return
    # Only jitter start; keep period at 300 to preserve cadence
    factor = random.uniform(0.9, 1.1)
    delay = max(5, int(base_delay * factor))
    try:
        if hasattr(m, "START_DELAY_SEC"):
            setattr(m, "START_DELAY_SEC", delay)
        if hasattr(m, "TEXT_START_DELAY_SEC"):
            setattr(m, "TEXT_START_DELAY_SEC", delay)
        log.info("[miner_jitter] %s: delay=%ss (base=%s, factor=%.2f)", tag, delay, base_delay, factor)
    except Exception as e:
        log.warning("[miner_jitter] set constants %s failed: %s", tag, e)

def _install():
    for mod_name, d, p, tag in TARGETS:
        _apply_jitter(mod_name, d, p, tag)

_install()
async def setup(_bot):  # overlay only
    return