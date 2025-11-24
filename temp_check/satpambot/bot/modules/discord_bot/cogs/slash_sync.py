from discord.ext import commands
import os, asyncio, logging, discord
from discord import app_commands

log = logging.getLogger("slash_sync")
AUTO_THRESHOLD = int(os.getenv("SLASH_SYNC_AUTO_THRESHOLD", "5"))
def _bool_env(name: str):
    v = os.getenv(name); 
    if v is None: return None
    return v.strip().lower() not in ("0","false","no","off")
class SlashSync(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot; self._synced=False; self._lock=asyncio.Lock()
    def _decide_mode(self) -> str:
        forced = _bool_env("SLASH_SYNC_PER_GUILD")
        if forced is True: return "per-guild"
        if forced is False:return "global"
        return "per-guild" if len(getattr(self.bot,'guilds',[]))<=AUTO_THRESHOLD else "global"
    @commands.Cog.listener()
    async def on_ready(self):
        async with self._lock:
            if self._synced: return
            try:
                mode=self._decide_mode()
                if mode=="per-guild":
                    ids=[g.id for g in self.bot.guilds]
                    for gid in ids: await self.bot.tree.sync(guild=discord.Object(id=gid))
                    log.info("[slash] auto per-guild sync: %s", ",".join(map(str,ids)) or "-")
                else:
                    await self.bot.tree.sync(); log.info("[slash] global sync ok (auto mode)")
            except Exception as e: log.exception("slash sync failed: %s", e)
            finally: self._synced=True
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        try: await self.bot.tree.sync(guild=discord.Object(id=guild.id)); log.info("[slash] synced new guild: %s", guild.id)
        except Exception as e: log.exception("sync new guild failed: %s", e)
    @app_commands.command(name="sync", description="Sinkronisasi slash (auto/global/guild/all-guilds).")
    @app_commands.describe(mode="auto | global | guild | all-guilds")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def sync_cmd(self, interaction: discord.Interaction, mode: str="auto"):
        mode=(mode or "auto").lower().strip()
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            if mode=="global":
                await self.bot.tree.sync(); return await interaction.followup.send("✅ Global sync OK.", ephemeral=True)
            if mode=="guild":
                gid=interaction.guild_id; await self.bot.tree.sync(guild=discord.Object(id=gid))
                return await interaction.followup.send(f"✅ Guild sync OK: {gid}", ephemeral=True)
            if mode in ("all-guilds","all","per-guild"):
                ids=[g.id for g in self.bot.guilds]
                for gid in ids: await self.bot.tree.sync(guild=discord.Object(id=gid))
                return await interaction.followup.send(f"✅ Per-guild sync OK: {', '.join(map(str,ids)) or '-'}", ephemeral=True)
            auto=self._decide_mode(); return await self.sync_cmd(interaction, auto)
        except Exception as e: await interaction.followup.send(f"❌ Sync gagal: `{e}`", ephemeral=True)
    @app_commands.command(name="sync-reset", description="Hapus & re-sync semua perintah untuk guild ini.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def sync_reset_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        gid=interaction.guild_id
        try:
            self.bot.tree.clear_commands(guild=discord.Object(id=gid))
            await self.bot.tree.sync(guild=discord.Object(id=gid))
            await interaction.followup.send(f"✅ Reset & re-sync guild `{gid}` selesai.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Gagal reset: `{e}`", ephemeral=True)
    @app_commands.command(name="reload", description="Reload 1 modul cog.")
    @app_commands.describe(module="Nama modul cog, contoh: clearchat")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def reload_cmd(self, interaction: discord.Interaction, module: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        candidates=[module,f"satpambot.bot.modules.discord_bot.cogs.{module}",f"bot.modules.discord_bot.cogs.{module}",f"modules.discord_bot.cogs.{module}"]
        last=None
        for ext in candidates:
            try: await self.bot.reload_extension(ext); return await interaction.followup.send(f"🔁 Reload OK: `{ext}`", ephemeral=True)
            except Exception as e: last=e
        await interaction.followup.send(f"❌ Reload gagal untuk `{module}`\n`{last}`", ephemeral=True)
async def setup(bot: commands.Bot): await bot.add_cog(SlashSync(bot))