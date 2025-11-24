# Overlay Bootstrap (phase 0): ensure TTS shim is installed before any cog imports
import logging
log = logging.getLogger(__name__)
try:
    __import__("satpambot.bot.modules.discord_bot.cogs.a04_tts_import_shim")
    log.info("[overlay_bootstrap_phase0] tts shim loaded")
except Exception as e:
    log.warning("[overlay_bootstrap_phase0] failed to load tts shim: %r", e)
