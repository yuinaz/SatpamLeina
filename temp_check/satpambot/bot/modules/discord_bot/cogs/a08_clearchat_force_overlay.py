import logging
import discord
from discord import app_commands
from discord.ext import commands

LOGGER = logging.getLogger(__name__)
DEFAULT_LIMIT = 50  # fallback aman; jika modul asli punya, akan override ketika merged

def _skip_pinned(m: discord.Message) -> bool:
    return not getattr(m, "pinned", False)

class ClearChatForceOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="clearchat")
    @commands.has_permissions(manage_messages=True)
    async def clearchat_cmd(self, ctx: commands.Context, limit: int = DEFAULT_LIMIT):
        try:
            deleted = await ctx.channel.purge(limit=limit, check=_skip_pinned, bulk=True)
            await ctx.reply(f"🧹 {len(deleted)} pesan (non-pinned) dihapus.", delete_after=3)
        except Exception as e:
            LOGGER.exception("clearchat purge failed: %s", e)
            await ctx.reply("⚠️ Gagal purge.", delete_after=5)

    @app_commands.command(name="clearchat", description="Delete recent messages immediately.")
    @app_commands.default_permissions(manage_messages=True)
    async def clearchat_slash(self, interaction: discord.Interaction, limit: int = DEFAULT_LIMIT):
        channel = interaction.channel
        try:
            deleted = await channel.purge(limit=limit, check=_skip_pinned, bulk=True)
            await interaction.response.send_message(
                f"🧹 {len(deleted)} pesan (non-pinned) dihapus.", ephemeral=True
            )
        except Exception as e:
            LOGGER.exception("clearchat slash purge failed: %s", e)
            await interaction.response.send_message("⚠️ Gagal purge.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ClearChatForceOverlay(bot))
