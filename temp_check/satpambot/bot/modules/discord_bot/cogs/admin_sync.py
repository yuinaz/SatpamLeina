
from discord.ext import commands
import os, logging
import discord

from discord import app_commands
from typing import Literal

log = logging.getLogger(__name__)

Choice = Literal["auto","global","guild","all-guilds","clear_global","clear_guild","copy_global_to_guild"]

class AdminSync(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="sync", description="Sinkronisasi slash: auto/global/guild/all-guilds/clear_global/clear_guild/copy_global_to_guild.")
    @app_commands.describe(mode="auto | global | guild | all-guilds | clear_global | clear_guild | copy_global_to_guild")
    async def do_sync(self, inter: discord.Interaction, mode: Choice = "auto"):
        try:
            await inter.response.defer(ephemeral=True, thinking=True)
        except Exception:
            pass

        tree = self.bot.tree
        gid_env = os.getenv("SB_GUILD_ID")
        guild = inter.guild

        try:
            if mode == "global":
                synced = await tree.sync()
                msg = f"Synced **{len(synced)}** commands ke **GLOBAL**."
            elif mode == "guild":
                if not guild: 
                    await inter.followup.send("❌ Harus dipanggil di dalam guild.", ephemeral=True); return
                synced = await tree.sync(guild=guild)
                msg = f"Synced **{len(synced)}** command ke guild **{guild.id}**."
            elif mode == "all-guilds":
                total = 0
                for g in self.bot.guilds:
                    res = await tree.sync(guild=g); total += len(res)
                msg = f"Synced ke **{len(self.bot.guilds)}** guild (total cmd entries: {total})."
            elif mode == "copy_global_to_guild":
                if not guild:
                    await inter.followup.send("❌ Harus dipanggil di dalam guild.", ephemeral=True); return
                tree.copy_global_to(guild=guild)
                synced = await tree.sync(guild=guild)
                msg = f"Copied global → guild & synced **{len(synced)}**."
            elif mode == "clear_global":
                tree.clear_commands(guild=None)
                await tree.sync()
                msg = "🧹 Cleared **GLOBAL** commands."
            elif mode == "clear_guild":
                if not guild:
                    await inter.followup.send("❌ Harus dipanggil di dalam guild.", ephemeral=True); return
                tree.clear_commands(guild=guild)
                await tree.sync(guild=guild)
                msg = f"🧹 Cleared commands untuk guild **{guild.id}**."
            else:  # auto
                if gid_env:
                    g = discord.Object(id=int(gid_env))
                    synced = await tree.sync(guild=g)
                    msg = f"(auto) Synced **{len(synced)}** ke guild **{gid_env}**."
                elif guild:
                    synced = await tree.sync(guild=guild)
                    msg = f"(auto) Synced **{len(synced)}** ke guild **{guild.id}**."
                else:
                    synced = await tree.sync()
                    msg = f"(auto) Synced **{len(synced)}** ke **GLOBAL**."

            await inter.followup.send(msg, ephemeral=True)
        except Exception as e:
            log.exception("sync error")
            await inter.followup.send(f"❌ Sync error: `{type(e).__name__}` {e}", ephemeral=True)
async def setup(bot: commands.Bot):
    await bot.add_cog(AdminSync(bot))