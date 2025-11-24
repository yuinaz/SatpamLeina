# a10_interval_overlay_import.py
# Apply balanced intervals AT IMPORT TIME (no setup(), no bot needed).
# - Patches module constants for phish & slang miners.
# - Sets ENV for text miner (it reads TEXT_MINER_* from os.environ).
import os
import logging
from importlib import import_module

log = logging.getLogger(__name__)

def _ival(name, default):
    v = os.getenv(name)
    try:
        return int(v) if v not in (None, "") else int(default)
    except Exception:
        return int(default)

# Balanced defaults
TEXT_DELAY = _ival("TEXT_MINER_DELAY_SEC", 30)
TEXT_EVERY = _ival("TEXT_MINER_INTERVAL_SEC", 300)
PHISH_DELAY = _ival("PHISH_MINER_DELAY_SEC", 35)
PHISH_EVERY = _ival("PHISH_MINER_INTERVAL_SEC", 300)
SLANG_DELAY = _ival("SLANG_MINER_DELAY_SEC", 40)
SLANG_EVERY = _ival("SLANG_MINER_INTERVAL_SEC", 300)

# Ensure text miner sees ENV values
os.environ.setdefault("TEXT_MINER_DELAY_SEC", str(TEXT_DELAY))
os.environ.setdefault("TEXT_MINER_INTERVAL_SEC", str(TEXT_EVERY))

# Patch constants for phish & slang miners
patches = [
    ("satpambot.bot.modules.discord_bot.cogs.phish_text_hourly_miner",
     {"START_DELAY_SEC": PHISH_DELAY, "PERIOD_SEC": PHISH_EVERY}),
    ("satpambot.bot.modules.discord_bot.cogs.slang_hourly_miner",
     {"START_DELAY_SEC": SLANG_DELAY, "PERIOD_SEC": SLANG_EVERY}),
]

for modname, kv in patches:
    try:
        m = import_module(modname)
        for k, v in kv.items():
            setattr(m, k, v)
        log.info("[a10_import] %s: delay=%ss every=%ss", modname.split(".")[-1], list(kv.values())[0], list(kv.values())[1])
    except Exception as e:
        log.warning("[a10_import] failed %s: %r", modname, e)
