# Overlay Bootstrap: include scope filter overlay (must run after memory compat)
import logging
log = logging.getLogger(__name__)

def _try(modname):
    try:
        __import__(modname)
        log.info("[overlay_bootstrap] loaded %s", modname)
    except Exception as e:
        log.warning("[overlay_bootstrap] %s failed: %r", modname, e)

# Phase 0 TTS shim (if present)
_try("satpambot.bot.modules.discord_bot.cogs.a00_overlay_bootstrap_phase0")

# Core overlays from previous patches (best effort)
_try("satpambot.bot.modules.discord_bot.cogs.a01_learning_passive_overlay")
_try("satpambot.bot.modules.discord_bot.cogs.a02_miner_accel_overlay")
_try("satpambot.bot.modules.discord_bot.cogs.a26_memory_upsert_compat_overlay")
_try("satpambot.bot.modules.discord_bot.cogs.a03_tts_guard_overlay")

# NEW: scope filter should come AFTER memory_upsert compat so it wraps the final callable
_try("satpambot.bot.modules.discord_bot.cogs.a27_learning_scope_filter_overlay")
