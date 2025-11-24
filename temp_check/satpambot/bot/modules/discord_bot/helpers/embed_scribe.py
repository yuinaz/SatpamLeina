# SPDX-License-Identifier: MIT
# Minimal, safe EmbedScribe helper — upsert a status message without spamming.
from __future__ import annotations

import logging
from typing import Optional, Any

import discord

log = logging.getLogger(__name__)

class EmbedScribe:
    @staticmethod
    async def upsert(
        bot: discord.Client,
        channel_id: int | str,
        content: Optional[str] = None,
        *,
        embed: Optional[discord.Embed] = None,
        marker: str = "[status_embed]",
        pin: bool = True,
        edit_only: bool = False,
        color: Optional[int] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        message_id: Optional[int] = None,
        **kwargs: Any,
    ) -> Optional[int]:
        """
        Upsert a single message in a channel with a stable 'marker' to avoid duplicates.
        Returns the message id on success, otherwise None.
        - If message_id given, try to edit that message.
        - Else: search pinned messages for `marker`, edit first match, otherwise send new.
        - No @mentions, no TTS, safe for Render free.
        """
        try:
            cid = int(str(channel_id).strip())
        except Exception:
            log.warning("[embed_scribe] invalid channel_id=%r", channel_id)
            return None

        ch = getattr(bot, "get_channel", lambda _id: None)(cid)
        if ch is None:
            # Try via cache-miss: fetch channel if possible (optional)
            log.warning("[embed_scribe] channel not found: %s", cid)
            return None

        # Build embed if title/description provided but embed missing
        if embed is None and (title or description):
            try:
                color_val = color if isinstance(color, int) else 0x3498db
                embed = discord.Embed(title=title or discord.Embed.Empty,
                                      description=description or discord.Embed.Empty,
                                      color=color_val)
            except Exception:
                embed = None

        try:
            # 1) If message_id provided, edit directly
            if message_id:
                try:
                    msg = await ch.fetch_message(int(message_id))
                    await msg.edit(content=(content or f"{marker}"), embed=embed)
                    if pin:
                        try: await msg.pin()
                        except Exception: pass
                    return msg.id
                except Exception:
                    # fallthrough to search+create
                    pass

            # 2) Search existing pinned messages that contain marker
            target = None
            try:
                pins = await ch.pins()
                for m in pins:
                    if marker and ((m.content and marker in m.content) or (m.embeds and any(marker in (m.embeds[0].footer.text or "") for _ in [0]))):
                        target = m
                        break
            except Exception:
                # pins() may require permissions; ignore
                pass

            if target is not None:
                try:
                    await target.edit(content=(content or target.content or f"{marker}"), embed=embed)
                    if pin:
                        try: await target.pin()
                        except Exception: pass
                    return target.id
                except Exception as e:
                    log.warning("[embed_scribe] edit failed: %r", e)

            if edit_only:
                # Do not create a new message if edit-only
                return None

            # 3) Send a new message
            try:
                msg = await ch.send(content=(content or f"{marker}"), embed=embed, silent=True)
                if pin:
                    try: await msg.pin()
                    except Exception: pass
                return msg.id
            except Exception as e:
                log.warning("[embed_scribe] send failed: %r", e)
                return None

        except Exception as e:
            log.exception("[embed_scribe] upsert exception: %r", e)
            return None
