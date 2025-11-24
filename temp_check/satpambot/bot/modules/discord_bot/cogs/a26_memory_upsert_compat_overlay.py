# Overlay: memory_upsert compatibility wrapper
import logging, importlib, inspect
log = logging.getLogger(__name__)

def _wrap():
    try:
        mem = importlib.import_module("satpambot.bot.modules.discord_bot.helpers.memory_upsert")
    except Exception as e:
        log.warning("[memory_upsert_compat_overlay] gagal import memory_upsert: %r", e); return
    orig = getattr(mem, "upsert_pinned_memory", None)
    if not callable(orig):
        log.warning("[memory_upsert_compat_overlay] upsert_pinned_memory tidak ditemukan"); return
    sig = inspect.signature(orig)

    def adapter(*args, **kwargs):
        try:
            return orig(*args, **kwargs)
        except TypeError:
            pass
        bot = kwargs.pop("bot", args[0] if args else None)
        payload = kwargs.pop("payload", args[1] if len(args) > 1 else None)
        gid = kwargs.pop("guild_id", None) or (payload.get("guild_id") if isinstance(payload, dict) else None)
        cid = kwargs.pop("channel_id", None) or (payload.get("channel_id") if isinstance(payload, dict) else None)
        title = kwargs.pop("title", None) or (payload.get("title") if isinstance(payload, dict) else "XP: Miner Memory")
        call_kwargs = {}
        for name in sig.parameters.keys():
            if name == "bot": call_kwargs["bot"] = bot
            elif name == "guild_id": call_kwargs["guild_id"] = gid
            elif name == "channel_id": call_kwargs["channel_id"] = cid
            elif name == "title": call_kwargs["title"] = title
            elif name == "payload": call_kwargs["payload"] = payload
        return orig(**call_kwargs)

    setattr(mem, "upsert_pinned_memory", adapter)
    log.info("[memory_upsert_compat_overlay] wrapper aktif")

_wrap()
