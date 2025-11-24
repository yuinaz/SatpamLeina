from discord.ext import commands
import os
import subprocess
import discord
from discord import app_commands

def _git_rev_short() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
        if out:
            return out
    except Exception:
        pass
    rev = os.getenv("RENDER_GIT_COMMIT", "")[:7]
    return rev or "unknown"


class AboutCard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="about", description="Tampilkan kartu info SatpamBot (guild-only).")
    async def about(self, inter: discord.Interaction):
        embed = discord.Embed(
            title="🤖 SatpamBot - Anti Phishing Discord Guard",
            description="Fitur utama:\n"
                        "• Anti‑Phishing (keyword & OCR)\n"
                        "• Auto Ban + log ke #mod-command\n"
                        "• Dashboard monitoring real-time\n"
                        "• Plugin manager & role maker\n"
                        "• Statistik server & user",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Versi", value=f"`{_git_rev_short()}`", inline=True)
        embed.add_field(name="Server", value=str(len(self.bot.guilds)), inline=True)
        await inter.response.send_message(embed=embed, ephemeral=True)
async def setup(bot: commands.Bot):
    await bot.add_cog(AboutCard(bot))