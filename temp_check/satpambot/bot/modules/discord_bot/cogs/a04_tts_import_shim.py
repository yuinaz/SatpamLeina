# Overlay: Import shim for tts_voice_reply — produce safe stub when TTS is disabled
import sys, types, logging
log = logging.getLogger(__name__)

def _cfg(key, default=None):
    try:
        from satpambot.config.runtime import cfg
        v = cfg(key)
        return default if v is None else v
    except Exception:
        return default

TARGET = "satpambot.bot.modules.discord_bot.cogs.tts_voice_reply"

class _TTSStubLoader:
    def create_module(self, spec):
        m = types.ModuleType(TARGET)
        async def setup(bot):  # pragma: no cover
            log.info("[tts_import_shim] TTS disabled (TTS_ENABLED=False). Stub loaded; skipping real TTS.")
        m.setup = setup
        return m
    def exec_module(self, module):  # pragma: no cover
        pass

class _TTSShimFinder:
    def find_spec(self, fullname, path, target=None):
        if fullname != TARGET:
            return None
        # Only stub when disabled
        enabled = bool(_cfg("TTS_ENABLED", False))
        if enabled:
            return None
        from importlib.machinery import ModuleSpec
        return ModuleSpec(TARGET, _TTSStubLoader())

# Insert finder at highest priority (front) if not already present
if not any(getattr(x, "__class__", None).__name__ == "_TTSShimFinder" for x in sys.meta_path):
    sys.meta_path.insert(0, _TTSShimFinder())
    log.info("[tts_import_shim] active (TTS_ENABLED=%s)", bool(_cfg("TTS_ENABLED", False)))

async def setup(bot):
    return None
