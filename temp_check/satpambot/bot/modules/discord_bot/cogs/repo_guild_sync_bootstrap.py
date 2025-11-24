from discord.ext import commands
import asyncio
import logging
import discord
from discord import app_commands

log = logging.getLogger(__name__)

# Opsional: isi dengan daftar guild id tertentu, atau biarkan kosong agar sync ke semua guild yang bot masuki
PREFERRED_GUILD_IDS: list[int] = []


class RepoGuildSyncBootstrap(commands.Cog):
    """Bootstrap kecil untuk memastikan group /repo tersinkron ke guild (guild-only).
    Tidak menyentuh ENV dan tidak mengubah command lain.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Jalankan bootstrap setelah bot ready
        self._task = asyncio.create_task(self._bootstrap())

    async def _bootstrap(self) -> None:
        await self.bot.wait_until_ready()
        # beri sedikit jeda agar cogs lain (termasuk pembuat /repo) sudah terdaftar
        await asyncio.sleep(2.0)

        tree: app_commands.CommandTree = self.bot.tree

        # Cari group /repo yang sudah dibuat oleh cog lain (mis. repo_slash_simple)
        repo_group = None
        for cmd in tree.get_commands():
            if isinstance(cmd, app_commands.Group) and cmd.name == "repo":
                repo_group = cmd
                break

        if repo_group is None:
            log.warning("[repo_guild_sync_bootstrap] /repo group tidak ditemukan di CommandTree; skip.")
            return

        if not self.bot.guilds:
            log.warning("[repo_guild_sync_bootstrap] Bot tidak berada di guild manapun; skip.")
            return

        guild_ids = [g.id for g in self.bot.guilds]
        if PREFERRED_GUILD_IDS:
            guild_ids = [gid for gid in guild_ids if gid in PREFERRED_GUILD_IDS] or guild_ids

        synced = 0
        for gid in guild_ids:
            gobj = discord.Object(id=gid)
            try:
                # Sync akan mendorong command tree ke guild tsb (guild-only untuk guild itu)
                await tree.sync(guild=gobj)
                synced += 1
                log.info("[repo_guild_sync_bootstrap] synced /repo ke guild %s", gid)
            except Exception as e:
                log.exception("[repo_guild_sync_bootstrap] Gagal sync ke guild %s: %r", gid, e)

        log.info("[repo_guild_sync_bootstrap] selesai; guild tersinkron: %d", synced)
async def setup(bot: commands.Bot):
    await bot.add_cog(RepoGuildSyncBootstrap(bot))