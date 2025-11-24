from __future__ import annotations

import logging
from satpambot.config.local_cfg import cfg
log = logging.getLogger(__name__)
try:
    from satpambot.bot.modules.discord_bot.cogs import neuro_governor_levels as ngl
    owners_cfg = str(cfg("NEURO_GOVERNOR_OWNERS", "") or "")
    owners = set()
    for s in owners_cfg.split(","):
        s = s.strip()
        if s.isdigit():
            owners.add(int(s))
    if owners:
        ngl.OWNERS = owners
        log.info("[governor_cfg_overlay] OWNERS <- %s", sorted(owners))
except Exception as e:
    log.warning("[governor_cfg_overlay] failed: %s", e)