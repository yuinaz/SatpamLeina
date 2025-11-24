from __future__ import annotations

from discord.ext import commands

# -*- coding: utf-8 -*-
"""
WarnReactionTamer
=================
Menghapus reaction ⚠️ di mana pun secepat mungkin (default ~0.2s).
- Hapus reaction dari SIAPA PUN (butuh permission Manage Messages di channel tsb).
- Support DM dan Guild.
Konfigurasi via env (opsional):
- WARN_REACTION_EMOJI: default "⚠️"
- WARN_REACTION_REMOVE_DELAY_S: default "0.2"  (maks 3.0 detik sesuai permintaan)
"""

import asyncio
import os
from typing import Optional

import discord

WARN_SET = {"\u26a0", "\u26a0\ufe0f", "⚠", "⚠️"}  # variasi unicode

def _is_warning_emoji(pe: discord.PartialEmoji, target: str) -> bool:
    # partial emoji jadi string bisa "<:name:id>" utk custom; utk unicode -> emoji unicode
    s = str(pe)
    # cocokkan untuk unicode
    if s in WARN_SET or pe.name in WARN_SET:
        return True
    # dukung override via env
    if target and (s == target or pe.name == target):
        return True
    return False

class WarnReactionTamer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # baca env
        self.warn_emoji = os.getenv("WARN_REACTION_EMOJI", "⚠️")
        try:
            self.delay = float(os.getenv("WARN_REACTION_REMOVE_DELAY_S", "0.2"))
        except Exception:
            self.delay = 0.2
        # hard cap 3.0s agar sesuai requirement
        if self.delay > 3.0:
            self.delay = 3.0

    async def _remove(self, payload: discord.RawReactionActionEvent) -> None:
        # optional delay (untuk menghindari race ketika message baru dipost)
        if self.delay > 0:
            await asyncio.sleep(self.delay)

        # resolve channel
        channel: Optional[discord.abc.Messageable] = None
        try:
            if payload.guild_id:
                guild = self.bot.get_guild(payload.guild_id) or await self.bot.fetch_guild(payload.guild_id)
                channel = guild.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
            else:
                # DM / group DM
                channel = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
        except Exception:
            # fetch fallback
            try:
                channel = await self.bot.fetch_channel(payload.channel_id)
            except Exception:
                return

        if channel is None:
            return

        # fetch message
        try:
            message = await channel.fetch_message(payload.message_id)
        except Exception:
            return

        # bangun emoji obj untuk remove
        emoji = payload.emoji
        try:
            # hapus reaction dari siapapun (butuh Manage Messages untuk non-self)
            await message.remove_reaction(emoji, discord.Object(id=payload.user_id))
        except Exception:
            # fallback: kalau gagal remove atas nama user, coba clear khusus emoji (butuh Manage Messages)
            try:
                await message.clear_reaction(emoji)
            except Exception:
                # tidak ada permission atau sudah hilang
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # filter: hanya warning emoji
        if _is_warning_emoji(payload.emoji, self.warn_emoji):
            # jadwalkan penghapusan cepat
            asyncio.create_task(self._remove(payload))
async def setup(bot: commands.Bot):
    await bot.add_cog(WarnReactionTamer(bot))