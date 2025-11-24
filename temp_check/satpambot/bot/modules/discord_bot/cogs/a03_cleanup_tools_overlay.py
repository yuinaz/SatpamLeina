# -*- coding: utf-8 -*-
"""
a03_cleanup_tools_overlay (enhanced)
/clearchat dan !clearchat untuk hapus non-pinned di STATUS_CHANNEL_ID
"""
from discord.ext import commands
import os, logging

try:
    from discord import app_commands
except Exception:
    app_commands=None
log=logging.getLogger(__name__)

class CleanupTools(commands.Cog):
    def __init__(self, bot):
        self.bot=bot; self.channel_id=int(os.getenv("STATUS_CHANNEL_ID","1400375184048787566"))

    async def _purge(self, channel, limit=1000):
        def check(m): return not getattr(m,"pinned",False)
        try:
            deleted=await channel.purge(limit=limit, check=check, bulk=True)
        except Exception:
            deleted=[]
            async for m in channel.history(limit=limit):
                try:
                    if not m.pinned:
                        await m.delete(); deleted.append(m)
                except Exception: pass
        return len(deleted)

    if app_commands is not None:
        @app_commands.command(name="clearchat", description="Hapus pesan non-pinned di status channel (spam cleaner).")
        async def clearchat_slash(self, interaction):
            if not interaction.user.guild_permissions.manage_messages:
                return await interaction.response.send_message("❌ Butuh izin Manage Messages.", ephemeral=True)
            ch=self.bot.get_channel(self.channel_id) or await self.bot.fetch_channel(self.channel_id)
            if ch is None: return await interaction.response.send_message("❌ Channel tidak ditemukan.", ephemeral=True)
            await interaction.response.defer(ephemeral=True, thinking=True)
            n=await self._purge(ch, limit=1000)
            await interaction.followup.send(f"🧹 Dibersihkan: {n} pesan (non-pinned).", ephemeral=True)

    @commands.command(name="clearchat")
    @commands.has_permissions(manage_messages=True)
    async def clearchat_text(self, ctx):
        ch=self.bot.get_channel(self.channel_id) or await self.bot.fetch_channel(self.channel_id)
        if ch is None: return await ctx.reply("❌ Channel tidak ditemukan.", mention_author=False)
        n=await self._purge(ch, limit=1000)
        await ctx.reply(f"🧹 Dibersihkan: {n} pesan (non-pinned).", mention_author=False)
async def setup(bot):
    cog=CleanupTools(bot); await bot.add_cog(cog)
    if app_commands is not None:
        try: bot.tree.add_command(cog.clearchat_slash)
        except Exception: pass
def setup(bot):
    try:
        import asyncio; loop=None
        try: loop=asyncio.get_event_loop()
        except RuntimeError: pass
        return loop.create_task(setup(bot)) if (loop and loop.is_running()) else asyncio.run(setup(bot))
    except Exception: return None