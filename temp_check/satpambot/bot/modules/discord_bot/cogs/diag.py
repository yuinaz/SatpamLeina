from discord.ext import commands
import discord
from discord import app_commands

class Diag(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="diag-slash", description="Tampilkan daftar slash command yang terdaftar.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def diag_slash(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        global_cmds = [c.name for c in self.bot.tree.get_commands()]
        try:
            guild_cmds = [c.name for c in self.bot.tree.get_commands(guild=discord.Object(id=interaction.guild_id))]
        except Exception:
            guild_cmds = []
        msg = ["**Slash (global)**: " + (', '.join(sorted(set(global_cmds))) or '-'),
               "**Slash (guild ini)**: " + (', '.join(sorted(set(guild_cmds))) or '-')]
        await interaction.followup.send('\n'.join(msg), ephemeral=True)

    @app_commands.command(name="diag-cogs", description="Tampilkan cogs/extension yang terload.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def diag_cogs(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        exts = sorted(getattr(self.bot, "extensions", {}).keys())
        flags = []
        flags.append("clearchat: " + ("✅" if any(x.endswith(".cogs.clearchat") for x in exts) else "❌"))
        flags.append("slash_sync: " + ("✅" if any(x.endswith(".cogs.slash_sync") for x in exts) else "❌"))
        await interaction.followup.send("Loaded extensions ({}):\n- ".format(len(exts)) + "\n- ".join(exts) + "\n\n" + ", ".join(flags), ephemeral=True)
async def setup(bot: commands.Bot):
    await bot.add_cog(Diag(bot))