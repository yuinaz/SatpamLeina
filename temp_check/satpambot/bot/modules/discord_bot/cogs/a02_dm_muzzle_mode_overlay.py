from __future__ import annotations

import logging, inspect, asyncio
from satpambot.config.local_cfg import cfg, cfg_int
log = logging.getLogger(__name__)
try:
    from satpambot.bot.modules.discord_bot.cogs import a02_dm_muzzle_strict as dmz
except Exception as e:
    dmz = None
    log.warning("[dm_muzzle_mode_overlay] base module not found: %s", e)
if dmz:
    mode = str(cfg("DM_MUZZLE", "") or "").strip().lower()
    if mode:
        try:
            setattr(dmz, "MODE", mode)
            log.info("[dm_muzzle_mode_overlay] MODE <- %s (from local.json)", mode)
        except Exception as e:
            log.debug("[dm_muzzle_mode_overlay] set MODE failed: %s", e)
    OWNER_ID = int(cfg_int("OWNER_USER_ID", 0) or 0)
    target_fn = None
    for name in dir(dmz):
        cand = getattr(dmz, name, None)
        if callable(cand) and name.lower().endswith("should_block_dm"):
            target_fn = cand
            break
    if target_fn and OWNER_ID:
        async def _as_async(func, *a, **kw):
            if inspect.iscoroutinefunction(func):
                return await func(*a, **kw)
            return func(*a, **kw)
        async def _owner_interactive_bypass(*a, **kw):
            author_id = None
            channel_is_dm = False
            for x in list(a) + list(kw.values()):
                try:
                    author_id = int(getattr(getattr(x, "author", None), "id", 0) or author_id or 0)
                    ch = getattr(x, "channel", None)
                    channel_is_dm = channel_is_dm or (getattr(ch, "type", None) and str(getattr(ch, "type")).lower().endswith("private"))
                except Exception:
                    pass
            if author_id and int(author_id) == int(OWNER_ID) and channel_is_dm:
                return False
            return await _as_async(target_fn, *a, **kw)
        setattr(dmz, target_fn.__name__, _owner_interactive_bypass)
        log.info("[dm_muzzle_mode_overlay] owner interactive bypass enabled for id=%s", OWNER_ID)