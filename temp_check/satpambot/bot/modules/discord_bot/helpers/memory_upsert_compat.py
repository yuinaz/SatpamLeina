# Helper: direct-compatible upsert_pinned_memory wrapper (use if you import this module)
import logging, importlib, inspect
log = logging.getLogger(__name__)

try:
    _mem = importlib.import_module("satpambot.bot.modules.discord_bot.helpers.memory_upsert")
    _orig = getattr(_mem, "upsert_pinned_memory", None)
except Exception as e:
    _mem, _orig = None, None
    log.warning("[memory_upsert_compat] gagal import memory_upsert: %r", e)

def upsert_pinned_memory(bot=None, payload=None, guild_id=None, channel_id=None, title=None):
    if not callable(_orig):
        raise RuntimeError("memory_upsert.upsert_pinned_memory tidak tersedia")
    sig = inspect.signature(_orig)
    call_kwargs = {}
    if "bot" in sig.parameters: call_kwargs["bot"] = bot
    if "guild_id" in sig.parameters: call_kwargs["guild_id"] = guild_id or (payload.get("guild_id") if isinstance(payload, dict) else None)
    if "channel_id" in sig.parameters: call_kwargs["channel_id"] = channel_id or (payload.get("channel_id") if isinstance(payload, dict) else None)
    if "title" in sig.parameters: call_kwargs["title"] = title or (payload.get("title") if isinstance(payload, dict) else "XP: Miner Memory")
    if "payload" in sig.parameters: call_kwargs["payload"] = payload
    return _orig(**call_kwargs)
