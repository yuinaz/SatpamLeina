# a00_miner_constants_overlay.py
# Early overlay to force miner constants BEFORE other cogs are imported.
# Reads config/miner_intervals.json, imports miner modules early, and sets module-level constants.
import logging, json
from pathlib import Path
from importlib import import_module
log = logging.getLogger(__name__)

DEFAULTS = {
    "text":  {"start": 30, "period": 300},
    "phish": {"start": 35, "period": 300},
    "slang": {"start": 40, "period": 300},
}

def _load_cfg():
    p = Path("config/miner_intervals.json")
    if p.exists():
        try:
            return {**DEFAULTS, **json.loads(p.read_text(encoding="utf-8"))}
        except Exception as e:
            log.warning("[a00_overlay] failed to read miner_intervals.json: %r", e)
    return DEFAULTS

CFG = _load_cfg()

def _patch(module_name: str, start_attr: str, period_attr: str, start_v: int, period_v: int) -> bool:
    try:
        m = import_module(f"satpambot.bot.modules.discord_bot.cogs.{module_name}")
    except Exception as e:
        log.debug("[a00_overlay] import %s failed (might not exist): %r", module_name, e)
        return False
    changed = False
    if hasattr(m, start_attr):
        try:
            setattr(m, start_attr, int(start_v)); changed = True
            log.info("[a00_overlay] %s.%s = %s", module_name, start_attr, start_v)
        except Exception:
            pass
    if hasattr(m, period_attr):
        try:
            setattr(m, period_attr, int(period_v)); changed = True
            log.info("[a00_overlay] %s.%s = %s", module_name, period_attr, period_v)
        except Exception:
            pass
    return changed

# Apply patches early
# Known attributes (from prior inspection):
# - phish/slang: START_DELAY_SEC, PERIOD_SEC
# - text: TEXT_START_DELAY_SEC, TEXT_PERIOD_SEC (fallback to START_DELAY_SEC/PERIOD_SEC)
_patch("phish_text_hourly_miner", "START_DELAY_SEC", "PERIOD_SEC", CFG["phish"]["start"], CFG["phish"]["period"])
_patch("slang_hourly_miner",      "START_DELAY_SEC", "PERIOD_SEC", CFG["slang"]["start"], CFG["slang"]["period"])
ok_text = _patch("text_activity_hourly_miner", "TEXT_START_DELAY_SEC", "TEXT_PERIOD_SEC", CFG["text"]["start"], CFG["text"]["period"])
if not ok_text:
    _patch("text_activity_hourly_miner", "START_DELAY_SEC", "PERIOD_SEC", CFG["text"]["start"], CFG["text"]["period"])
