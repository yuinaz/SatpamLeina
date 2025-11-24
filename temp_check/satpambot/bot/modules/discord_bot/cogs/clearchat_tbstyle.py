import logging
import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)

MAX_LIMIT = 200  # batas aman

def _skip_pinned(m: discord.Message) -> bool:
    return not getattr(m, "pinned", False)

@app_commands.command(name="clearchat", description="Bersihkan sejumlah pesan dari channel ini.")
@app_commands.default_permissions(manage_messages=True)
async def clearchat(interaction: discord.Interaction, jumlah: app_commands.Range[int, 1, MAX_LIMIT] = 50):
    # Permission guard (tetap dipertahankan agar double-safe)
    perms = getattr(interaction.user, "guild_permissions", None)
    if interaction.guild and (not perms or not perms.manage_messages):
        return await interaction.response.send_message(
            "❌ Kamu perlu **Manage Messages** di channel ini untuk menjalankan /clearchat.",
            ephemeral=True
        )

    channel = interaction.channel
    try:
        deleted = await channel.purge(limit=jumlah, check=_skip_pinned, bulk=True, reason=f"/clearchat by {interaction.user}")
        return await interaction.response.send_message(f"🧹 {len(deleted)} pesan (non-pinned) dihapus.", ephemeral=True)
    except Exception:
        log.exception("[clearchat_tbstyle] purge gagal")
        return await interaction.response.send_message("⚠️ Gagal purge.", ephemeral=True)

async def setup(bot: commands.Bot):
    bot.tree.add_command(clearchat)
