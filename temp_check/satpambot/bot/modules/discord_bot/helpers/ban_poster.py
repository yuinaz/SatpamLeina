from __future__ import annotations

# satpambot/bot/modules/discord_bot/helpers/ban_poster.py

import os
from typing import Optional

import discord
from discord.ext import commands

from .log_utils import find_text_channel
from modules.discord_bot.helpers.ban_embed import build_ban_embed, reason_hash
from ..utils.actions import delete_message_safe

async def _find_existing_with_marker(
    channel: discord.TextChannel,
    marker: str,
    *,
    bot_user_id: Optional[int],
    history_limit: int = 50,
) -> Optional[discord.Message]:
    """Cari pesan embed lama dengan footer BAN_MARKER::<marker> (anti-spam dobel)."""
    try:
        async for m in channel.history(limit=history_limit, oldest_first=False):
            if bot_user_id is not None and getattr(m.author, "id", None) != bot_user_id:
                continue
            try:
                if not m.embeds:
                    continue
                ft = getattr(m.embeds[0].footer, "text", "") or ""
                if isinstance(ft, str) and f"BAN_MARKER::{marker}" in ft:
                    return m
            except Exception:
                continue
    except Exception:
        pass
    return None

def _resolve_log_channel(ctx: commands.Context) -> Optional[discord.TextChannel]:
    """
    Prefer ENV:
      - LOG_CHANNEL_ID (atau LOG_CHANNEL_ID_RAW)
      - LOG_CHANNEL_NAME
    Fallback: channel saat ini, atau text-channel pertama yang bisa kirim.
    """
    guild = getattr(ctx, "guild", None)
    if guild is None:
        return None

    cid_raw = os.getenv("LOG_CHANNEL_ID") or os.getenv("LOG_CHANNEL_ID_RAW")
    cname = os.getenv("LOG_CHANNEL_NAME")

    if cid_raw and cid_raw.strip().isdigit():
        ch = find_text_channel(guild, channel_id=int(cid_raw.strip()))
        if ch:
            return ch  # type: ignore

    if cname and cname.strip():
        ch = find_text_channel(guild, name=cname.strip())
        if ch:
            return ch  # type: ignore

    if isinstance(ctx.channel, discord.TextChannel):
        return ctx.channel

    return find_text_channel(guild)

async def post_ban_embed(
    ctx: commands.Context,
    target: discord.abc.User,
    reason: str = "Spam/Phishing",
    *,
    delete_command: bool = True,
    dedupe_by: str = "user+reason",
) -> Optional[discord.Message]:
    """
    Kirim/embed BAN seragam ke channel log (tanpa sticker). Dedupe default: user+reason.
    Jika sudah ada embed dengan marker yang sama, pesan lama di-edit, bukan kirim baru.
    """
    guild = getattr(ctx, "guild", None)
    ch = _resolve_log_channel(ctx)
    if ch is None:
        try:
            await ctx.reply("❗ Tidak menemukan channel log yang valid.", mention_author=False)
        except Exception:
            pass
        return None

    moderator = getattr(ctx, "author", None) or getattr(ctx, "user", None)
    if moderator is None:
        moderator = ctx.me or getattr(ctx.bot, "user", None)  # type: ignore

    if dedupe_by == "user":
        marker = f"{getattr(target, 'id', '0')}"
    else:
        marker = f"{getattr(target, 'id', '0')}|{reason_hash(reason)}"

    emb = build_ban_embed(guild=guild, moderator=moderator, target=target, reason=reason, marker=marker)

    bot_user_id = getattr(getattr(ctx, "me", None) or getattr(ctx.bot, "user", None), "id", None)
    old = await _find_existing_with_marker(ch, marker, bot_user_id=bot_user_id)

    if old:
        try:
            await old.edit(embed=emb)
            msg = old
            status = "updated"
        except Exception:
            msg = await ch.send(embed=emb)
            status = "sent"
    else:
        msg = await ch.send(embed=emb)
        status = "sent"

    if delete_command and getattr(ctx, "message", None):
        try:
            await delete_message_safe(ctx.message)
        except Exception:
            pass

    try:
        await ctx.reply(f"✅ Ban {status} → {msg.jump_url}", mention_author=False, delete_after=8)
    except Exception:
        pass

    return msg

async def perform_ban_and_post(
    ctx: commands.Context,
    target: discord.Member,
    reason: str = "Spam/Phishing",
    *,
    delete_days: int = 1,
) -> Optional[discord.Message]:
    """
    (Opsional) Lakukan ban beneran lalu post embed-nya. Kalau gagal ban, tetap post embed.
    """
    try:
        await target.ban(reason=reason, delete_message_days=delete_days)  # type: ignore[arg-type]
    except Exception:
        # abaikan; tetap kirim embed log supaya moderator tahu perintahnya jalan
        pass

    return await post_ban_embed(ctx, target, reason)