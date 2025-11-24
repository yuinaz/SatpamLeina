from __future__ import annotations

import logging, os
from typing import Optional
import discord

log = logging.getLogger(__name__)

def _to_int(x:str)->int:
    try: return int((x or '').strip())
    except Exception: return 0

def _resolve_error_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    """Resolve error-log channel with robust defaults.
    Priority:
      1) ERROR_LOG_CHANNEL_ID (ENV)
      2) DEFAULT_ERROR_CHANNEL_ID (1404288516195880960)
      3) By name: ERROR_LOG_CHANNEL_NAME (ENV), else common fallbacks
    """
    # 1) ENV ID
    try:
        cid_env = os.getenv("ERROR_LOG_CHANNEL_ID", "").strip()
        if cid_env.isdigit():
            ch = guild.get_channel(int(cid_env))
            if isinstance(ch, discord.TextChannel):
                return ch
    except Exception:
        pass
    # 2) Built-in default ID
    try:
        ch = guild.get_channel(DEFAULT_ERROR_CHANNEL_ID)
        if isinstance(ch, discord.TextChannel):
            return ch
    except Exception:
        pass
    # 3) Name resolution
    candidates = [
        os.getenv("ERROR_LOG_CHANNEL_NAME", "").strip(),
        "errorlog-bot", "errorlog_bot", "errorlogbot",
        "error-log-bot", "error-log", "errorlog", "errlog",
    ]
    for nm in [c for c in candidates if c]:
        for tc in getattr(guild, "text_channels", []) or []:
            try:
                if isinstance(tc, discord.TextChannel) and tc.name.lower() == nm.lower():
                    return tc
            except Exception:
                continue
    return None

# --- compat: add log_error_embed if missing ---
try:
    log_error_embed
except NameError:
    import discord  # type: ignore
    async def log_error_embed(channel, title: str, description: str):
        try:
            emb = discord.Embed(title=title, description=description, color=0xE74C3C)
            await channel.send(embed=emb)
        except Exception:
            # Fallback teks supaya tidak memutus alur
            try:
                await channel.send(f"[ERROR] {title}: {description}")
            except Exception:
                pass
