from __future__ import annotations

from discord.ext import commands
import discord

from satpambot.config.local_cfg import cfg

HELP = ("Pencarian web belum dikonfigurasi. "
        "Tambahkan kunci API/engine di `local.json` lalu aktifkan cog web_search aslinya. "
        "Sementara, gunakan `/webhelp` untuk petunjuk konfigurasi.")

class WebSearchFallback(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.hybrid_command(name="webhelp", description="Cara mengaktifkan pencarian web yang aman")
    async def webhelp(self, ctx: commands.Context):
        emb = discord.Embed(title="Web Search Helper",
                            description="Agar bot bisa mencari di web, isi konfigurasi berikut di `local.json`:")
        emb.add_field(name="WEB_SEARCH_PROVIDER", value="mis: `ddg` atau `serpapi`", inline=False)
        emb.add_field(name="SERPAPI_KEY", value="(opsional) kunci SerpAPI jika pakai provider `serpapi`", inline=False)
        emb.add_field(name="SEARCH_SAFE_MODE", value="`true` untuk safe search default", inline=False)
        emb.set_footer(text="Setelah diisi, load cog web_search asli. Fallback ini aman & tidak error.")
        await ctx.reply(embed=emb)
async def setup(bot): await bot.add_cog(WebSearchFallback(bot))