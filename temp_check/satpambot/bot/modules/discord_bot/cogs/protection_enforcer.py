from __future__ import annotations

from discord.ext import commands

# -*- coding: utf-8 -*-
"""
protection_enforcer.py
----------------------
Lindungi channel & role tertentu dari aksi-aksi yang tidak diinginkan.
- Mencegah penghapusan pesan di channel 'mod-command' (patch ringan).
- Menyediakan util untuk cek role exempt (Admin/Moderator).

Tidak memakai ENV; nama channel & role bisa diubah di konstanta.
"""

import logging
import discord

LOG = logging.getLogger(__name__)

SAFE_CHANNEL_NAMES = {"mod-command"}
EXEMPT_ROLE_NAMES = {"Admin", "Moderator"}

class ProtectionEnforcer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Patch ringan: cegah Message.delete di channel aman (no-op wrapper)
        def _wrap_delete(orig_delete):
            async def _safe_delete(msg, *a, **kw):
                ch = getattr(msg, "channel", None)
                name = getattr(ch, "name", "") if ch else ""
                if name in SAFE_CHANNEL_NAMES:
                    LOG.info("[protection_enforcer] skip delete di #%s", name)
                    return  # no-op
                return await orig_delete(msg, *a, **kw)
            return _safe_delete

        # monkeypatch method di class Message hanya sekali
        if not getattr(discord.Message.delete, "_patched_by_satpambot", False):
            discord.Message._orig_delete = discord.Message.delete
            discord.Message.delete = _wrap_delete(discord.Message.delete)
            setattr(discord.Message.delete, "_patched_by_satpambot", True)
            LOG.info("[protection_enforcer] Patched Message.delete untuk channel aman: %s", ", ".join(SAFE_CHANNEL_NAMES))
async def setup(bot: commands.Bot):
    await bot.add_cog(ProtectionEnforcer(bot))
    LOG.info("[protection_enforcer] aktif")