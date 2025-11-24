from __future__ import annotations

import logging
from satpambot.config.local_cfg import cfg_int
log = logging.getLogger(__name__)
PREFERRED_IDS = [
    int(cfg_int("PROGRESS_THREAD_ID", 0) or 0),
    int(cfg_int("LEARNING_PROGRESS_THREAD_ID", 0) or 0),
]
def _pick_id():
    for x in PREFERRED_IDS:
        try:
            if int(x) > 0:
                return int(x)
        except Exception:
            pass
    return 0
try:
    target_id = _pick_id()
    if target_id:
        try:
            from satpambot.bot.modules.discord_bot.cogs import progress_thread_reuse_shim as shim
            setattr(shim, "PREFERRED_THREAD_ID", target_id)
            if hasattr(shim, "LearningProgress"):
                LP = getattr(shim, "LearningProgress")
                orig = getattr(LP, "ensure_thread", None)
                if callable(orig):
                    async def ensure_thread_pref(self, *a, **kw):
                        ch = getattr(self, "_channel", None)
                        if ch is not None:
                            try:
                                t = await ch.fetch_thread(target_id)
                                if t:
                                    return t
                            except Exception:
                                pass
                        return await orig(self, *a, **kw)
                    setattr(LP, "ensure_thread", ensure_thread_pref)
                    log.info("[progress_explicit_thread] prefer %s", target_id)
        except Exception as e:
            log.warning("[progress_explicit_thread] shim patch failed: %s", e)
        try:
            from satpambot.bot.modules.discord_bot.cogs import progress_thread_relay as relay
            setattr(relay, "PREFERRED_THREAD_ID", target_id)
            log.info("[progress_explicit_thread] relay.PREFERRED_THREAD_ID = %s", target_id)
        except Exception as e:
            log.warning("[progress_explicit_thread] relay patch failed: %s", e)
except Exception as e:
    log.warning("[progress_explicit_thread] failed: %s", e)