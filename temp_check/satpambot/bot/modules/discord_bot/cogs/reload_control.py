
# reload_control.py (GroupCog version with auto guild sync once)
from discord.ext import commands
import asyncio
import traceback
import discord

from discord import app_commands

COG_PREFIX = "satpambot.bot.modules.discord_bot.cogs."

def normalize_cog(name: str) -> str:
    n = name.strip().replace("\\", ".").replace("/", ".")
    if n.endswith(".py"):
        n = n[:-3]
    if n.startswith(COG_PREFIX):
        return n
    if "." not in n:
        return COG_PREFIX + n
    return n

def has_manage_guild(interaction: discord.Interaction) -> bool:
    m = getattr(interaction, "user", None)
    if not isinstance(m, discord.Member):
        return False
    perms = m.guild_permissions
    return perms.administrator or perms.manage_guild

class ReloadControl(commands.GroupCog, name="reload"):
    """Admin-only control to reload cogs and resync app commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- Slash commands ----------
    @app_commands.command(name="cog", description="Reload a specific cog by name (file name or full module path).")
    @app_commands.describe(name="Nama cog. Contoh: whitelist  atau  satpambot.bot.modules.discord_bot.cogs.whitelist")
    @app_commands.default_permissions(manage_guild=True)
    async def cog(self, interaction: discord.Interaction, name: str):
        if not has_manage_guild(interaction):
            await interaction.response.send_message("❌ Kamu butuh izin **Manage Server**.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        modname = normalize_cog(name)
        try:
            if modname in self.bot.extensions:
                self.bot.reload_extension(modname)
            else:
                self.bot.load_extension(modname)
            await interaction.followup.send(f"✅ Reload OK: `{modname}`", ephemeral=True)
        except Exception as e:
            tb = traceback.format_exc(limit=2)
            await interaction.followup.send(f"❌ Gagal reload: `{modname}`\n```\n{e}\n{tb}\n```", ephemeral=True)

    @app_commands.command(name="all", description="Reload semua cogs yang saat ini loaded.")
    @app_commands.default_permissions(manage_guild=True)
    async def all(self, interaction: discord.Interaction):
        if not has_manage_guild(interaction):
            await interaction.response.send_message("❌ Kamu butuh izin **Manage Server**.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        loaded = list(self.bot.extensions.keys())
        ok, fail = [], []
        for modname in loaded:
            try:
                self.bot.reload_extension(modname)
                ok.append(modname)
            except Exception as e:
                fail.append((modname, str(e)))
        msg = f"✅ Reloaded: {len(ok)} cogs.\n"
        if ok:
            msg += "```\n" + "\n".join(ok) + "\n```\n"
        if fail:
            msg += f"❌ Failed: {len(fail)}\n```\n" + "\n".join(f"{m} :: {err}" for m,err in fail) + "\n```"
        await interaction.followup.send(msg, ephemeral=True)

    @app_commands.command(name="sync", description="Resync slash commands (app commands) ke server ini.")
    @app_commands.default_permissions(manage_guild=True)
    async def sync(self, interaction: discord.Interaction):
        if not has_manage_guild(interaction):
            await interaction.response.send_message("❌ Kamu butuh izin **Manage Server**.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            res = await self.bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send(f"✅ Synced {len(res)} command(s) ke guild `{interaction.guild.name}`.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Gagal sync: ```\n{e}\n```", ephemeral=True)

    # ---------- Optional: prefix commands ----------
    @commands.group(name="reload", invoke_without_command=True)
    @commands.has_guild_permissions(manage_guild=True)
    async def reload_text(self, ctx: commands.Context):
        await ctx.reply("Gunakan: `!reload cog <name>` atau `!reload all` atau `/reload ...`", mention_author=False)

    @reload_text.command(name="cog")
    @commands.has_guild_permissions(manage_guild=True)
    async def reload_text_cog(self, ctx: commands.Context, *, name: str):
        modname = normalize_cog(name)
        try:
            if modname in self.bot.extensions:
                self.bot.reload_extension(modname)
            else:
                self.bot.load_extension(modname)
            await ctx.reply(f"✅ Reload OK: `{modname}`", mention_author=False)
        except Exception as e:
            await ctx.reply(f"❌ Gagal reload `{modname}`:\n```\n{e}\n```", mention_author=False)

    @reload_text.command(name="all")
    @commands.has_guild_permissions(manage_guild=True)
    async def reload_text_all(self, ctx: commands.Context):
        loaded = list(self.bot.extensions.keys())
        ok, fail = [], []
        for modname in loaded:
            try:
                self.bot.reload_extension(modname)
                ok.append(modname)
            except Exception as e:
                fail.append((modname, str(e)))
        msg = f"✅ Reloaded: {len(ok)} cogs.\n"
        if ok:
            msg += "```\n" + "\n".join(ok) + "\n```\n"
        if fail:
            msg += f"❌ Failed: {len(fail)}\n```\n" + "\n".join(f"{m} :: {err}" for m,err in fail) + "\n```"
        await ctx.reply(msg, mention_author=False)

async def _sync_all_guilds_once(bot: commands.Bot):
    """Sync commands to all joined guilds once after ready (instant propagation)."""
    await bot.wait_until_ready()
    try:
        for g in bot.guilds:
            try:
                await bot.tree.sync(guild=g)
            except Exception:
                pass
    except Exception:
        pass
async def setup(bot: commands.Bot):
    # Register the GroupCog
    await bot.add_cog(ReloadControl(bot))
    # One-time guild sync (non-blocking)
    asyncio.create_task(_sync_all_guilds_once(bot))