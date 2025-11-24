# --- XP contract integration (non-invasive) ---
try:
    from satpambot.shared.xp_store import XpStore  # type: ignore
    _XPSTORE_AVAILABLE = True
except Exception:
    _XPSTORE_AVAILABLE = False

def _xp_debug_dump(logger):
    if not _XPSTORE_AVAILABLE:
        logger.debug("[xp_overlay] XpStore not available"); return
    try:
        xs = XpStore()
        senior = xs.get_senior_total()
        kuliah = xs.get_ladder_kuliah()
        magang = xs.get_ladder_magang()
        pref   = xs.get_curriculum_pref()
        logger.info("[xp_overlay] SENIOR=%s pref=%s KULIAH=%s MAGANG=%s",
                    senior, pref, sorted(kuliah.items()), sorted(magang.items()))
    except Exception as e:
        logger.warning("[xp_overlay] xp debug failed: %r", e)
