from __future__ import annotations

import logging
from satpambot.config.local_cfg import cfg_int
log = logging.getLogger(__name__)
try:
    from satpambot.bot.modules.discord_bot.cogs import a02_dm_muzzle_strict as dmz
    def _get_focus_id_cfg():
        v = dmz.os.getenv("LOG_CHANNEL_ID") or ""
        try:
            return int(v)
        except Exception:
            pass
        return int(cfg_int("LOG_CHANNEL_ID", 0) or 0)
    dmz._get_focus_id = _get_focus_id_cfg
    log.info("[dm_muzzle_cfg_overlay] patched _get_focus_id to use local.json fallback")
except Exception as e:
    log.warning("[dm_muzzle_cfg_overlay] failed: %s", e)