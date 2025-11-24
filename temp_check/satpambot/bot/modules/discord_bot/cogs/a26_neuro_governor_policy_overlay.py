from __future__ import annotations

import logging
from satpambot.config.local_cfg import cfg_int, cfg_bool, cfg

log = logging.getLogger(__name__)

DEFAULTS = {
    "GOV_MIN_DAYS": 2,
    "GOV_MIN_XP": 2500,
    "GOV_MATURE_ERR_RATE": 0.03,  # 3%
    "GOV_REQUIRE_QNA_APPROVAL": True,
}

def _get(k, cast=float):
    v = cfg(k, None)
    if v is None:
        if k in DEFAULTS:
            return DEFAULTS[k]
        return None
    try:
        if cast is int:
            return int(v)
        if cast is bool:
            return str(v).lower() in ("1","true","yes","on")
        return float(v)
    except Exception:
        return DEFAULTS.get(k)

try:
    from satpambot.bot.modules.discord_bot.cogs import neuro_governor_levels as ngl
    # Inject thresholds from local.json
    ngl.MIN_DAYS = int(_get("GOV_MIN_DAYS", int))
    ngl.MIN_XP   = int(_get("GOV_MIN_XP", int))
    ngl.MATURE_ERR_RATE = float(_get("GOV_MATURE_ERR_RATE"))
    ngl.REQUIRE_QNA_APPROVAL = bool(_get("GOV_REQUIRE_QNA_APPROVAL", bool))
    log.info("[governor_policy] MIN_DAYS=%s MIN_XP=%s MATURE_ERR_RATE=%.3f REQUIRE_QNA_APPROVAL=%s",
             ngl.MIN_DAYS, ngl.MIN_XP, ngl.MATURE_ERR_RATE, ngl.REQUIRE_QNA_APPROVAL)
except Exception as e:
    log.warning("[governor_policy] overlay failed: %s", e)