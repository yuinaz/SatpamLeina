# modules/discord_bot/helpers/env.py  — unified, backward‑compatible
# - Keeps legacy constants (NSFW_INVITE_AUTOBAN, etc.) so cogs can import
# - Robust LOG_CHANNEL_ID parsing (handles quotes) + fallback by NAME
# - Token resolution supports DISCORD_BOT_TOKEN_LOCAL (local) & others
# - Additive: tidak menghapus fitur lama

import os
import re
import discord

# ---------- helpers ----------
def _first(*keys, default: str | None = None) -> str | None:
    for k in keys:
        v = os.getenv(k)
        if v:
            return v
    return default

def _bool(x: str | None, default=False) -> bool:
    if x is None:
        return default
    return str(x).strip().lower() in ("1", "true", "yes", "on")

def _to_int(x: str | None, default: int = 0) -> int:
    """Parse int safely; remove quotes & non-digits so '\"1400...\"' works."""
    try:
        s = str(x).strip()
        if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
            s = s[1:-1].strip()
        if not s.isdigit():
            s = re.sub(r"\D", "", s)
        return int(s) if s else default
    except Exception:
        return default

# ---------- tokens / intents / basic ----------
# Keep BOT_TOKEN available for old paths; prefer local-friendly order
BOT_TOKEN = _first("BOT_TOKEN", "DISCORD_TOKEN", "DISCORD_BOT_TOKEN", "DISCORD_BOT_TOKEN_LOCAL")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")  # optional mirror
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
FLASK_ENV = os.getenv("FLASK_ENV", "production")

def build_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.guilds = True
    return intents

BOT_INTENTS = build_intents()

# ---------- legacy feature toggles (required by some cogs) ----------
NSFW_INVITE_AUTOBAN  = _bool(os.getenv("NSFW_INVITE_AUTOBAN", "true"), default=True)
URL_AUTOBAN_CRITICAL = _bool(os.getenv("URL_AUTOBAN_CRITICAL", "true"), default=True)
URL_RESOLVE_ENABLED  = _bool(os.getenv("URL_RESOLVE_ENABLED", "true"), default=True)
OCR_SCAM_STRICT      = _bool(os.getenv("OCR_SCAM_STRICT", "true"), default=True)
OCR_LANG             = os.getenv("OCR_LANG", "eng+ind")

# ---------- log channels (ID and/or NAME) ----------
LOG_CHANNEL_ID_RAW     = os.getenv("LOG_CHANNEL_ID", "0").strip()
LOG_CHANNEL_NAME       = os.getenv("LOG_CHANNEL_NAME", "log-botphising").strip()
BAN_LOG_CHANNEL_ID_RAW = os.getenv("BAN_LOG_CHANNEL_ID", "0").strip()
BAN_LOG_CHANNEL_NAME   = os.getenv("BAN_LOG_CHANNEL_NAME", "").strip()

LOG_CHANNEL_ID   = _to_int(LOG_CHANNEL_ID_RAW, 0)
BAN_LOG_CHANNEL_ID = _to_int(BAN_LOG_CHANNEL_ID_RAW, 0)

async def resolve_log_channel(guild: discord.Guild):
    """Try ID, else exact NAME in text channels."""
    if LOG_CHANNEL_ID:
        ch = guild.get_channel(LOG_CHANNEL_ID)
        if ch:
            return ch
    name = LOG_CHANNEL_NAME.lstrip("#").strip()
    if name:
        for ch in guild.text_channels:
            if ch.name == name:
                return ch
    return None

async def resolve_ban_log_channel(guild: discord.Guild):
    if BAN_LOG_CHANNEL_ID:
        ch = guild.get_channel(BAN_LOG_CHANNEL_ID)
        if ch:
            return ch
    name = BAN_LOG_CHANNEL_NAME.lstrip("#").strip()
    if name:
        for ch in guild.text_channels:
            if ch.name == name:
                return ch
    # fallback to general log channel
    return await resolve_log_channel(guild)

# ---------- debug helper ----------
def env_log_summary() -> str:
    return (f"LOG_CHANNEL_ID_RAW='{LOG_CHANNEL_ID_RAW}' parsed={LOG_CHANNEL_ID} "
            f"LOG_CHANNEL_NAME='{LOG_CHANNEL_NAME}'")
