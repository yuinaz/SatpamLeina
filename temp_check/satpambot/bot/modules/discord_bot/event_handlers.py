# modules/discord_bot/events/event_handlers.py (fixed)
# - Clean try/except blocks (no syntax errors)
# - No stray decorators; all events registered inside register_event_handlers(bot)
# - Works with ENV-based log channel resolver if available
# - Keeps legacy behavior (channel names & ingest) — additive, nothing removed

import os
import re
import sqlite3
from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands

# Optional resolver (ID->NAME) if helpers.env exists
try:
    from satpambot.bot.modules.discord_bot.helpers import env as _env
except Exception:
    _env = None  # fallback to name-only lookups

# === DB config ===
DB_PATH = os.getenv("DB_PATH", "superadmin.db")

def _db_upsert_guild(guild: discord.Guild) -> None:
    try:
        gid = str(guild.id)
        name = guild.name
        icon_url = str(guild.icon.url) if getattr(guild, "icon", None) else None
        mc = getattr(guild, "member_count", None) or 0
        ja = None
        try:
            me = guild.me
            if getattr(me, "joined_at", None):
                ja = me.joined_at.isoformat()
        except Exception:
            pass
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_guilds (
                    guild_id TEXT PRIMARY KEY,
                    name TEXT,
                    member_count INTEGER,
                    icon_url TEXT,
                    joined_at TEXT
                )
            """)
            conn.execute("""
                INSERT INTO bot_guilds (guild_id, name, member_count, icon_url, joined_at)
                VALUES (?,?,?,?,?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    name=excluded.name,
                    member_count=excluded.member_count,
                    icon_url=excluded.icon_url,
                    joined_at=COALESCE(bot_guilds.joined_at, excluded.joined_at)
            """, (gid, name, mc, icon_url, ja))
            conn.commit()
    except Exception as e:
        print("[guilds] upsert fail", e)

def _db_remove_guild(guild_id: str) -> None:
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM bot_guilds WHERE guild_id=?", (str(guild_id),))
            conn.commit()
    except Exception as e:
        print("[guilds] remove fail", e)

# === Ingest (HTTP) ===
INGEST_URL = os.getenv("INGEST_URL", "https://satpambot.onrender.com/ingest/ban")
INGEST_TOKEN = os.getenv("INGEST_TOKEN", "Musedash123")

async def _post_ingest(payload: dict) -> None:
    try:
        import aiohttp
        async with aiohttp.ClientSession() as sess:
            await sess.post(
                INGEST_URL, json=payload,
                headers={"X-INGEST-TOKEN": INGEST_TOKEN}, timeout=15
            )
    except Exception as e:
        print("[ingest] failed", e)

# === Utilities ===
async def _resolve_log_channel(guild: discord.Guild) -> Optional[discord.TextChannel]:
    """Try helpers.env resolver (ID->NAME). Fallback to name 'log-botphising'."""
    # Prefer robust env resolver if available
    if _env is not None and hasattr(_env, "resolve_log_channel"):
        try:
            ch = await _env.resolve_log_channel(guild)  # type: ignore[attr-defined]
            if isinstance(ch, discord.TextChannel):
                return ch
        except Exception:
            pass
    # Fallback to known default name
    return discord.utils.get(guild.text_channels, name="log-botphising")

def _get_channel_by_name(guild: discord.Guild, name: str) -> Optional[discord.TextChannel]:
    return discord.utils.get(guild.text_channels, name=name)

# === Notifications ===
async def notify_bot_active(guild: discord.Guild, bot_name: str):
    log_channel = await _resolve_log_channel(guild)
    if log_channel:
        try:
            await log_channel.send(
                f"🟢 Bot aktif sebagai **{bot_name}** pada {datetime.now():%Y-%m-%d %H:%M:%S}"
            )
        except Exception as e:
            print("[notify] bot_active failed", e)

async def notify_ban_embed(guild: discord.Guild, user: discord.User, reason: str):
    log_channel = _get_channel_by_name(guild, "log-satpam-chat")
    if log_channel:
        try:
            embed = discord.Embed(
                title="🚫 Pengguna Terbanned",
                description=f"{user.mention} telah dibanned.\n**Alasan:** {reason}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="SatpamBot Security")
            await log_channel.send(embed=embed)
        except Exception as e:
            print("[notify] ban_embed failed", e)

async def notify_unban_embed(guild: discord.Guild, user: discord.User, moderator_name: str = "Moderator", reason: str = "Unban manual"):
    log_channel = _get_channel_by_name(guild, "log-satpam-chat")
    if log_channel:
        try:
            embed = discord.Embed(
                title="✅ Pengguna Di-unban",
                description=f"{user.mention} telah di-unban.\n**Oleh:** {moderator_name}\n**Alasan:** {reason}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="SatpamBot Security")
            await log_channel.send(embed=embed)
        except Exception as e:
            print("[notify] unban_embed failed", e)

async def notify_to_ngobrol(guild: discord.Guild, user: discord.User, reason: str):
    ngobrol_ch = _get_channel_by_name(guild, "💬︲ngobrol") or guild.get_channel(886534544688308265)
    if ngobrol_ch:
        try:
            embed = discord.Embed(
                title="💀 Pengguna Terkick SatpamBot",
                description=f"{user.mention} telah dibanned karena {reason}.",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="🧹 Dibersihkan oleh SatpamBot")
            await ngobrol_ch.send(embed=embed)

            if sticker:
                await ngobrol_ch.send(stickers=[sticker])
        except Exception as e:
            print("[notify] ngobrol failed", e)

# === Message-based ingest (from external bot logs) ===
LOG_BAN_CHANNEL_NAME = os.getenv("LOG_BAN_CHANNEL_NAME", "log-satpam")
LOG_BAN_CHANNEL_ID = int(os.getenv("LOG_BAN_CHANNEL_ID", "0"))

def _first_id_from_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"(\\d{17,20})", text)
    return m.group(1) if m else None

def _extract_user_id_from_message(msg) -> Optional[str]:
    # Try regular content
    uid = _first_id_from_text(getattr(msg, "content", ""))
    # Inspect embeds (Carl-bot style)
    for emb in getattr(msg, "embeds", []) or []:
        for part in [getattr(emb, "description", None), getattr(emb, "title", None),
                     getattr(getattr(emb, "footer", None), "text", None),
                     getattr(getattr(emb, "author", None), "name", None)]:
            uid = uid or _first_id_from_text(part)
    return uid

async def on_message_parser(msg):
    # Filter channel by name or explicit ID (if provided)
    ch_id = getattr(getattr(msg, "channel", None), "id", None)
    ch_name = getattr(getattr(msg, "channel", None), "name", "")
    if LOG_BAN_CHANNEL_ID:
        if ch_id != LOG_BAN_CHANNEL_ID:
            return
    else:
        if ch_name != LOG_BAN_CHANNEL_NAME:
            return

    # Determine action from text or embed title
    text = (msg.content or "").lower()
    titles = []
    for emb in getattr(msg, "embeds", []) or []:
        if getattr(emb, "title", None):
            titles.append(emb.title.lower())
        if getattr(emb, "description", None):
            text += " " + emb.description.lower()
    is_ban = ("member banned" in " ".join(titles)) or (" banned" in text)
    is_unban = ("member unbanned" in " ".join(titles)) or (" unbanned" in text) or ("unban" in text)

    uid = _extract_user_id_from_message(msg)
    if not uid:
        return

    guild_id = str(getattr(getattr(msg, "guild", None), "id", 0))
    if is_ban and not is_unban:
        await _post_ingest({"action": "ban", "user_id": uid, "guild_id": guild_id})
    elif is_unban:
        await _post_ingest({"action": "unban", "user_id": uid, "guild_id": guild_id})

# === Registrar ===
def register_event_handlers(bot: commands.Bot):
    @bot.event
    async def on_ready():
        try:
            # Kirim tanda bot aktif ke setiap guild (jika channel ada)
            for guild in bot.guilds:
                try:
                    await notify_bot_active(guild, str(bot.user))
                except Exception as e:
                    print("[event_handlers] notify_bot_active error", e)
            print("[event_handlers] on_ready sent notify_bot_active")
        except Exception as e:
            print("[event_handlers] on_ready error", e)

    @bot.event
    async def on_member_ban(guild, user):
        try:
            await notify_ban_embed(guild, user, reason="Pelanggaran aturan")
        except Exception as e:
            print("[event_handlers] on_member_ban notify error", e)
        try:
            await _post_ingest({"action": "ban", "user_id": str(user.id), "username": str(user), "guild_id": str(guild.id)})
        except Exception as e:
            print("[event_handlers] ingest ban error", e)

    @bot.event
    async def on_member_unban(guild, user):
        try:
            await notify_unban_embed(guild, user, moderator_name="Moderator", reason="Unban manual")
        except Exception as e:
            print("[event_handlers] on_member_unban notify error", e)
        try:
            await _post_ingest({"action": "unban", "user_id": str(user.id), "username": str(user), "guild_id": str(guild.id)})
        except Exception as e:
            print("[event_handlers] ingest unban error", e)

    @bot.event
    async def on_message(message):
        try:
            await on_message_parser(message)
        except Exception as e:
            print("[event_handlers] on_message parser error", e)

    @bot.event
    async def on_guild_join(guild):
        try:
            _db_upsert_guild(guild)
        except Exception as e:
            print("[event_handlers] on_guild_join db error", e)

    @bot.event
    async def on_guild_remove(guild):
        try:
            _db_remove_guild(guild.id)
        except Exception as e:
            print("[event_handlers] on_guild_remove db error", e)

    return bot
