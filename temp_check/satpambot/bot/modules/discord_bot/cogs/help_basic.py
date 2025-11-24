from __future__ import annotations

from discord.ext import commands

import datetime

import discord


def _wib_now_str() -> str:
    tz = datetime.timezone(datetime.timedelta(hours=7))
    return datetime.datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S WIB")


class HelpBasic(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="help", help="Tampilkan ringkasan perintah prefix penting.")
    async def help_cmd(self, ctx: commands.Context) -> None:
        emb = discord.Embed(title="📘 Bantuan — Prefix Commands", colour=discord.Colour.blue())
        emb.add_field(
            name="💀 Simulasi Ban — `!tb`",
            value=(
                "Simulasi tanpa aksi nyata. Bisa **reply** ke pesan lalu ketik `!tb [alasan?]`, "
                "atau `!tb @user [alasan]`. Hasil embed menampilkan **Lokasi, Alasan,** dan timestamp **WIB**.\n"
                "Contoh: `!tb` (sambil reply pesan)"
            ),
            inline=False
        )
        emb.add_field(
            name="🔨 Ban — `!ban`",
            value=(
                "Ban permanen. Bot membutuhkan permission ban pada server & channel ini.\n"
                "Contoh: `!ban @user promosi phishing`"
            ),
            inline=False
        )
        emb.set_footer(text=f"SatpamBot Help • {_wib_now_str()}")
        await ctx.reply(embed=emb)
async def setup(bot: commands.Bot) -> None:
    # Override default help agar konsisten
    try:
        bot.remove_command("help")
    except Exception:
        pass
    await bot.add_cog(HelpBasic(bot))