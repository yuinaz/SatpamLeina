import logging
import discord
from discord import app_commands
from discord.ext import commands

LOG = logging.getLogger(__name__)

MAX_LIMIT = 200  # batas aman maksimal

def _skip_pinned(m: discord.Message) -> bool:
    return not getattr(m, "pinned", False)

@app_commands.command(
    name="clearchat",
    description="Bersihkan pesan (DM/guild). Bisa filter embed, webhooks, judul embed."
)
@app_commands.default_permissions(manage_messages=True)
async def clearchat(
    interaction: discord.Interaction,
    jumlah: app_commands.Range[int, 1, MAX_LIMIT] = 50,
):
    # Guard runtime tambahan
    if interaction.guild:
        perms = getattr(interaction.user, "guild_permissions", None)
        if not perms or not perms.manage_messages:
            return await interaction.response.send_message(
                "❌ Kamu perlu **Manage Messages** di channel ini untuk menjalankan /clearchat.",
                ephemeral=True,
            )

    # DM mode
    if interaction.guild is None:
        try:
            if interaction.user.dm_channel is None:
                await interaction.user.create_dm()
            deleted = 0
            async for m in interaction.user.dm_channel.history(limit=jumlah):
                if m.author.id == interaction.client.user.id and not m.pinned:
                    await m.delete()
                    deleted += 1
            return await interaction.response.send_message(
                f"✅ DM dibersihkan: {deleted} pesan.", ephemeral=True
            )
        except Exception:
            LOG.exception("[public_clearchat] gagal scan DM")
            return await interaction.response.send_message(
                "⚠️ Gagal membersihkan DM.", ephemeral=True
            )

    # Guild mode
    channel = interaction.channel
    try:
        deleted_msgs = await channel.purge(limit=jumlah, check=_skip_pinned, bulk=True)
        return await interaction.response.send_message(
            f"🧹 Bersih! {len(deleted_msgs)} pesan (non-pinned).",
            ephemeral=True,
        )
    except Exception as e:
        LOG.exception("[public_clearchat] purge gagal: %s", e)
        return await interaction.response.send_message(
            "⚠️ Gagal menjalankan purge.", ephemeral=True
        )

async def setup(bot: commands.Bot):
    bot.tree.add_command(clearchat)
