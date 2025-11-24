from __future__ import annotations

# satpambot/bot/modules/discord_bot/helpers/ban_embed.py

import hashlib
from typing import Optional
import discord

def _avatar_url(user: discord.abc.User) -> Optional[str]:
    try:
        if getattr(getattr(user, "display_avatar", None), "url", None):
            return user.display_avatar.url  # type: ignore
        if getattr(getattr(user, "avatar", None), "url", None):
            return user.avatar.url  # type: ignore
    except Exception:
        pass
    return None

def _color_from_guild(guild: Optional[discord.Guild]) -> int:
    # Warna merah moderate untuk ban/testban
    return 0xED4245

def reason_hash(guild_id: int, target_id: int, reason: str) -> str:
    raw = f"{guild_id}:{target_id}:{reason or ''}".encode("utf-8", "ignore")
    return hashlib.sha1(raw).hexdigest()[:12]

def build_ban_embed(
    guild: discord.Guild,
    target: discord.Member | discord.User,
    moderator: discord.Member | discord.User | None,
    reason: str = "",
) -> discord.Embed:
    marker = reason_hash(getattr(guild, "id", 0), getattr(target, "id", 0), reason or "")
    desc = (
        f"**Target:** {getattr(target, 'mention', getattr(target, 'name', 'user'))} ({getattr(target, 'id', '—')})\n"
        f"**Moderator:** {getattr(moderator, 'mention', getattr(moderator, 'name', '—'))}\n"
        f"**Reason:** {reason.strip() or '—'}"
    )
    emb = discord.Embed(
        title="Ban/TestBan Notice",
        description=desc,
        color=_color_from_guild(guild),
    )
    av = _avatar_url(target)
    if av:
        emb.set_author(name=getattr(target, "name", "user"), icon_url=av)
    else:
        emb.set_author(name=getattr(target, "name", "user"))
    emb.set_footer(text=f"BAN_MARKER::{marker}")
    return emb
