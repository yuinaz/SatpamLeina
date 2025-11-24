# a02_balanced_interval_overlay.py
# Inject balanced delay/interval into miner modules without editing originals.
# Loads at import time (no setup() needed).
import os
import logging
from importlib import import_module

log = logging.getLogger(__name__)

def _int(name, default):
    try:
        v = os.getenv(name)
        return int(v) if v not in (None, "") else int(default)
    except Exception:
        return int(default)

# Defaults aimed at avoiding 429 while keeping progress steady
TEXT_DELAY = _int("TEXT_MINER_DELAY_SEC", 30)
TEXT_EVERY = _int("TEXT_MINER_INTERVAL_SEC", 300)
PHISH_DELAY = _int("PHISH_MINER_DELAY_SEC", 35)
PHISH_EVERY = _int("PHISH_MINER_INTERVAL_SEC", 300)
SLANG_DELAY = _int("SLANG_MINER_DELAY_SEC", 40)
SLANG_EVERY = _int("SLANG_MINER_INTERVAL_SEC", 300)

PATCHES = [
    ("satpambot.bot.modules.discord_bot.cogs.text_activity_hourly_miner",
     {"TEXT_START_DELAY_SEC": TEXT_DELAY, "TEXT_PERIOD_SEC": TEXT_EVERY}),
    ("satpambot.bot.modules.discord_bot.cogs.phish_text_hourly_miner",
     {"START_DELAY_SEC": PHISH_DELAY, "PERIOD_SEC": PHISH_EVERY}),
    ("satpambot.bot.modules.discord_bot.cogs.slang_hourly_miner",
     {"START_DELAY_SEC": SLANG_DELAY, "PERIOD_SEC": SLANG_EVERY}),
]

for modname, kv in PATCHES:
    try:
        m = import_module(modname)
        for k, v in kv.items():
            setattr(m, k, v)
        log.info("[interval_overlay] %s: delay=%ss every=%ss", modname.split(".")[-1], list(kv.values())[0], list(kv.values())[1])
    except Exception as e:
        log.warning("[interval_overlay] failed %s: %r", modname, e)
