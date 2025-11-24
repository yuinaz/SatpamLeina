from __future__ import annotations

from discord.ext import commands


class BanAliasCog(commands.Cog):
    """Alias/forwarder untuk ban jika diperlukan oleh konfigurasi lama.
    Aman untuk smoke test (DummyBot) karena semua akses get_command dibungkus try/except.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="ban", help="Ban permanen.")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, *args):
        # Jika ada command 'ban' lain yang lebih spesifik, panggil itu.
        target_cmd = None
        try:
            # Beberapa setup menamai command asli tetap "ban"
            target_cmd = self.bot.get_command("ban")  # type: ignore[attr-defined]
        except Exception:
            target_cmd = None

        # Hindari rekursi: jika target adalah command ini sendiri, biarkan ctx.bot resolve ke cogs lain
        if target_cmd is not None and target_cmd.callback is not self.ban.callback:  # type: ignore[attr-defined]
            return await target_cmd.callback(self, ctx, *args)  # type: ignore[misc]

        # Jika tidak ada implementasi lain, berikan pesan yang ramah
        await ctx.reply(
            "⚠️ Target command untuk 'ban' tidak ditemukan (cari: ban/tempban/tban). "
            "Cek cogs moderasi kamu.",
            mention_author=False,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(BanAliasCog(bot))