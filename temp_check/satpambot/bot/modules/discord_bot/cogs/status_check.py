from discord.ext import commands
import os
import time
import subprocess
import discord
from discord import app_commands

_PROC_START = time.time()


def _git_rev_short() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
        if out:
            return out
    except Exception:
        pass
    rev = os.getenv("RENDER_GIT_COMMIT", "")[:7]
    return rev or "unknown"


class StatusCheck(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="status", description="Cek status bot & repo (guild-only).")
    async def status(self, inter: discord.Interaction):
        uptime = int(time.time() - _PROC_START)
        guilds = len(self.bot.guilds)
        msg = f"✅ **Online** | guilds: **{guilds}** | uptime: **{uptime}s** | commit: `{_git_rev_short()}`"
        await inter.response.send_message(msg, ephemeral=True)
async def setup(bot: commands.Bot):
    await bot.add_cog(StatusCheck(bot))