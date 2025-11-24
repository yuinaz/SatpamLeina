import os
import logging

log = logging.getLogger(__name__)

def _env_int(name: str):
    v = os.getenv(name)
    if not v:
        return None
    try:
        return int(v)
    except Exception:
        return None

def _env_guild_id(bot):
    # Prefer ENV, fallback ke guild pertama bot kalau ada
    return _env_int("GUILD_METRICS_ID") or (bot.guilds[0].id if getattr(bot, "guilds", None) else None)

def _env_public_report_channel_id():
    # Prefer PUBLIC_REPORT_CHANNEL_ID, fallback ke LOG_CHANNEL_ID
    return _env_int("PUBLIC_REPORT_CHANNEL_ID") or _env_int("LOG_CHANNEL_ID")

DEFAULT_TITLE = os.getenv("MEMORY_UPSERT_TITLE", "XP: Miner Memory")

# --- import original helper ---
from satpambot.bot.modules.discord_bot.helpers.memory_upsert import upsert_pinned_memory as _original

async def _patched_memroute(bot, *args, **kwargs):
    '''
    Wrapper aman untuk upsert_pinned_memory:
      - Bentuk baru: upsert_pinned_memory(bot, payload_dict)
      - Bentuk lama: upsert_pinned_memory(bot, guild_id, channel_id, title, **kwargs)
    '''
    # CASE-1: new-style (bot, payload_dict)
    if len(args) == 1 and isinstance(args[0], dict) and not kwargs:
        payload = args[0]

        guild_id = payload.get("guild_id") or _env_guild_id(bot)
        channel_id = payload.get("channel_id") or _env_public_report_channel_id()
        title = payload.get("title") or DEFAULT_TITLE

        if not guild_id or not channel_id:
            log.error("[memroute] payload kurang field wajib (guild_id/channel_id). keys=%s", list(payload.keys()))
            return False

        # PENTING: kirim sebagai payload=payload (jangan **payload)
        return await _original(bot, guild_id, channel_id, title, payload=payload)

    # CASE-2: legacy passthrough
    return await _original(bot, *args, **kwargs)

# Monkey-patch helper agar semua import downstream pakai wrapper ini
from satpambot.bot.modules.discord_bot.helpers import memory_upsert as _helper_mod
_helper_mod.upsert_pinned_memory = _patched_memroute
