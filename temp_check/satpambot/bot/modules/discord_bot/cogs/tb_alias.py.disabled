from __future__ import annotations

from discord.ext import commands

# Alias "tb" hanya aktif bila belum ada command `tb` (mis. dari tb_shim).
# Jika tidak ada, alias ini akan mencoba meneruskan ke tban/tempban/ban.

FORWARD_CANDIDATES = ("tban", "tempban", "ban")

class TBAliasCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _resolve_target(self):
        getc = getattr(self.bot, "get_command", None)
        if not callable(getc):
            return None
        for name in FORWARD_CANDIDATES:
            cmd = getc(name)
            if cmd is not None:
                return cmd
        return None

    @commands.command(name="tb", help="Alias ke tban/tempban/ban bila `!tb` belum tersedia.")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def tb_alias(self, ctx: commands.Context, *args):
        target_cmd = self._resolve_target()
        if target_cmd is None:
            await ctx.reply(
                "⚠️ Target command untuk 'ban' tidak ditemukan (cari: ban/tempban/tban). "
                "Cek cogs moderasi kamu.", mention_author=False
            )
            return
        await ctx.invoke(target_cmd, *args)


async def setup(bot: commands.Bot):
    getc = getattr(bot, "get_command", None)
    if callable(getc) and getc("tb") is not None:
        # Sudah ada tb (mis. tb_shim) — biarkan itu yang aktif, jangan dobel
        return
    await bot.add_cog(TBAliasCog(bot))