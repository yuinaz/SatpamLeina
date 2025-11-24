import logging
from satpambot.bot.modules.discord_bot.helpers import env
from satpambot.bot.modules.discord_bot.helpers.log_once import log_once

def log_env_summary_once():
    log_once("env_log_summary", lambda: logging.info("[status] %s", env.env_log_summary()))

def log_selected_channel(ch, by: str = "id"):
    key = f"log_channel_resolved:{getattr(ch,'id',None)}"
    def _p():
        tag = " (by name)" if by == "name" else ""
        logging.info("[status] using log channel%s: #%s (id=%s) in guild='%s' (id=%s)",
                     tag, getattr(ch, "name", "?"), getattr(ch, "id", "?"),
                     getattr(getattr(ch, "guild", None), "name", "?"),
                     getattr(getattr(ch, "guild", None), "id", "?"))
    log_once(key, _p)

def warn_no_log_channel_once():
    log_once("no_log_channel_found", lambda: logging.warning("[status] no log channel found via ID or NAME."))

async def announce_status(guild, bot=None):
    # Cetak summary ENV sekali saja
    log_env_summary_once()
    # Resolve + log channel sekali
    ch = await env.resolve_log_channel(guild)
    if ch:
        # nggak perlu spam; cukup sekali per channel id
        log_selected_channel(ch, by="id")
        return ch
    warn_no_log_channel_once()
    return None
