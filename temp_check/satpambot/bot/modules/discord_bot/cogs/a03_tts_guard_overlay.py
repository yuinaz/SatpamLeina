# Overlay: Guard TTS so it won't crash on missing voice deps (Render-safe default OFF)
import logging, importlib
from typing import Any, Callable, Awaitable

log = logging.getLogger(__name__)

def _cfg(key: str, default=None):
    try:
        from satpambot.config.runtime import cfg
        v = cfg(key)
        return default if v is None else v
    except Exception:
        return default

def _patch_tts():
    ENABLED = bool(_cfg("TTS_ENABLED", False))  # default OFF on Render
    modname = "satpambot.bot.modules.discord_bot.cogs.tts_voice_reply"
    try:
        mod = importlib.import_module(modname)
    except Exception as e:
        log.warning("[tts_guard] %s not importable: %r", modname, e)
        return
    setup = getattr(mod, "setup", None)
    if not callable(setup):
        log.info("[tts_guard] no setup() in %s", modname); return

    async def safe_setup(bot):
        if not ENABLED:
            log.info("[tts_guard] TTS disabled by config (TTS_ENABLED=False). Skipping %s", modname)
            return
        try:
            await setup(bot)
            log.info("[tts_guard] TTS loaded")
        except Exception as e:
            log.warning("[tts_guard] TTS failed to load: %r. Temporarily disabled.", e)

    setattr(mod, "setup", safe_setup)

_patch_tts()
async def setup(bot):
    return None
