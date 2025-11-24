from discord.ext import commands
import discord
from discord import app_commands

class DiagPublic(commands.Cog):
    def __init__(self, bot): self.bot = bot
    @app_commands.command(name="diag-public", description="Daftar cepat nama slash command (global & guild).")
    @app_commands.guild_only()
    async def diag_public(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        names = sorted({c.name for c in self.bot.tree.get_commands()})
        try: gnames = sorted({c.name for c in self.bot.tree.get_commands(guild=discord.Object(id=interaction.guild_id))})
        except Exception: gnames = []
        await interaction.followup.send("**Global:** " + (', '.join(names) or '-') + "\n**Guild:** " + (', '.join(gnames) or '-'), ephemeral=True)
async def setup(bot): await bot.add_cog(DiagPublic(bot))