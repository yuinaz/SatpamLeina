from __future__ import annotations

# -*- coding: utf-8 -*-
"""
unban_fix.py
------------
Command aman untuk unban ID, memperbaiki error konversi & iterator ban.

Gunakan:
  !unbanid 123456789012345678
  !unbanid <@123456789012345678>
  !unbanid well... (123456789012345678)

Tidak mengubah command "unban" lama; ini berdampingan.
"""


import re
import logging
import discord
from discord.ext import commands

LOG = logging.getLogger(__name__)
ID_RE = re.compile(r"(\d{15,25})")

class UnbanFix(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="unbanid", aliases=["unban_safe", "unbanfix"])
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def unbanid(self, ctx: commands.Context, *, raw: str):
        """Unban berdasarkan ID/mention/string yang mengandung ID."""
        m = ID_RE.search(raw or "")
        if not m:
            return await ctx.send("❌ Tidak menemukan ID di argumen. Contoh: `!unbanid 123456789012345678`")

        uid = int(m.group(1))

        # Jalur cepat: langsung unban dengan Object
        try:
            user_obj = discord.Object(id=uid)
            await ctx.guild.unban(user_obj, reason=f"UnbanFix by {ctx.author}")
            return await ctx.send(f"✅ Unbanned ID `{uid}` (jalur cepat).")
        except discord.NotFound:
            # Tidak ada di banlist; mungkin sudah ter-unban
            return await ctx.send(f"ℹ️ ID `{uid}` tidak ada di daftar ban.")
        except discord.Forbidden:
            return await ctx.send("❌ Bot tidak punya izin unban.")
        except Exception as e:
            LOG.warning("Jalur cepat unban gagal: %r — lanjut cek daftar ban", e)

        # Fallback: iterasi daftar ban dengan async for
        target_entry = None
        try:
            async for ban_entry in ctx.guild.bans(limit=None):
                if int(ban_entry.user.id) == uid:
                    target_entry = ban_entry
                    break
        except Exception as e:
            LOG.exception("Gagal mengambil daftar ban: %r", e)
            return await ctx.send("❌ Gagal mengambil daftar ban (lihat log).")

        if not target_entry:
            return await ctx.send(f"ℹ️ ID `{uid}` tidak ditemukan di daftar ban.")

        try:
            await ctx.guild.unban(target_entry.user, reason=f"UnbanFix by {ctx.author}")
            return await ctx.send(f"✅ Unbanned **{target_entry.user}** (`{uid}`).")
        except Exception as e:
            LOG.exception("Gagal unban: %r", e)
            return await ctx.send("❌ Unban gagal (lihat log).")

async def setup(bot: commands.Bot):
    await bot.add_cog(UnbanFix(bot))
    LOG.info("[unban-fix] command siap (unbanid/unban_safe/unbanfix)")