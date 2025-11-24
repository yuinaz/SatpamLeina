# Overlay: Learning Passive Observer tuning (Render-safe)
import logging, importlib
from typing import Any

log = logging.getLogger(__name__)

def _cfg(key: str, default: Any):
    try:
        from satpambot.config.runtime import cfg
        v = cfg(key)
        return default if v is None else v
    except Exception:
        return default

def _to_int(val, default):
    try:
        if isinstance(val, (int, float)): return int(val)
        ss = str(val).strip().rstrip(",").replace("_","").replace(" ","")
        try: return int(ss)
        except Exception: return int(float(ss))
    except Exception: return int(default)

def _to_float(val, default):
    try:
        if isinstance(val, (int, float)): return float(val)
        ss = str(val).strip().rstrip(",")
        return float(ss)
    except Exception: return float(default)
    try:
        from satpambot.config.runtime import cfg
        v = cfg(key)
        return default if v is None else v
    except Exception:
        return default

def _patch_learning():
    try:
        mod = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.learning_passive_observer")
    except Exception as e:
        log.warning("[learning_overlay] gagal import learning_passive_observer: %r", e)
        return

    XP_WINDOW_SEC      = _to_int(_cfg("LEARN_XP_WINDOW_SEC", 30), 30)
    XP_CAP_PER_WINDOW  = _to_int(_cfg("LEARN_XP_CAP_PER_WINDOW", 50), 50)
    MIN_DELTA_ITEMS    = _to_int(_cfg("LEARN_MIN_DELTA_ITEMS", 12), 12)

    XP_PER_ITEM_TEXT   = _to_float(_cfg("LEARN_XP_PER_ITEM_TEXT", 0.4), 0.4)
    XP_PER_ITEM_SLANG  = _to_float(_cfg("LEARN_XP_PER_ITEM_SLANG", 0.8), 0.8)
    XP_PER_ITEM_PHISH  = _to_float(_cfg("LEARN_XP_PER_ITEM_PHISH", 1.2), 1.2)

    BURST_ON_BOOT      = bool(_cfg("LEARN_PASSIVE_BURST_ON_BOOT", True))
    BURST_MULTIPLIER   = _to_float(_cfg("LEARN_BURST_MULTIPLIER", 1.5), 1.5)
    BURST_DURATION_SEC = _to_int(_cfg("LEARN_BURST_DURATION_SEC", 600), 600)

    for k, v in {
        "XP_WINDOW_SEC":XP_WINDOW_SEC,
        "XP_CAP_PER_WINDOW":XP_CAP_PER_WINDOW,
        "MIN_DELTA_ITEMS":MIN_DELTA_ITEMS,
        "XP_PER_ITEM_TEXT":XP_PER_ITEM_TEXT,
        "XP_PER_ITEM_SLANG":XP_PER_ITEM_SLANG,
        "XP_PER_ITEM_PHISH":XP_PER_ITEM_PHISH,
        "BURST_ON_BOOT":BURST_ON_BOOT,
        "BURST_MULTIPLIER":BURST_MULTIPLIER,
        "BURST_DURATION_SEC":BURST_DURATION_SEC,
    }.items():
        setattr(mod, k, v)

    log.info("[learning_overlay] patched window=%s cap=%s min_delta=%s xp=%.2f/%.2f/%.2f burst=%s x%.1f %ss",
             XP_WINDOW_SEC, XP_CAP_PER_WINDOW, MIN_DELTA_ITEMS,
             XP_PER_ITEM_TEXT, XP_PER_ITEM_SLANG, XP_PER_ITEM_PHISH,
             BURST_ON_BOOT, BURST_MULTIPLIER, BURST_DURATION_SEC)

_patch_learning()
async def setup(bot):
    return None
