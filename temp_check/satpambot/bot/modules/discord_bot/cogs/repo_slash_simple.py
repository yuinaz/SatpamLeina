
# satpambot/bot/modules/discord_bot/cogs/repo_slash_simple.py
from discord.ext import commands
import asyncio, os, sys, subprocess, logging, importlib, json, time
import discord
from discord import app_commands

log = logging.getLogger(__name__)
TICKET_PATH = "/tmp/restart_ticket.json"

class RepoSlashSimple(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _git_pull_hard(self) -> str:
        cmds = [
            ["git","fetch","--all","--prune"],
            ["git","reset","--hard","origin/main"],
            ["git","submodule","update","--init","--recursive"],
        ]
        for cmd in cmds:
            proc = await asyncio.to_thread(
                subprocess.run, cmd, check=True, capture_output=True, text=True
            )
            log.info("[repo] %s -> %s", " ".join(cmd), proc.stdout.strip())

        head = await asyncio.to_thread(
            subprocess.run, ["git","rev-parse","--short","HEAD"],
            check=True, capture_output=True, text=True
        )
        return head.stdout.strip()

    async def _hard_restart(self):
        await asyncio.sleep(0.4)
        importlib.invalidate_caches()
        python = sys.executable
        os.execv(python, [python, "main.py"])

    @app_commands.command(name="pull", description="Hard pull origin/main lalu restart")
    async def repo_pull(self, itx: discord.Interaction):
        try:
            await itx.response.defer(thinking=True, ephemeral=False)
        except discord.InteractionResponded:
            pass
        try:
            sha = await self._git_pull_hard()
        except Exception as e:
            log.exception("git hard pull gagal")
            return await itx.followup.send(f"❌ Hard pull gagal: `{e}`")

        msg = await itx.followup.send(f"✅ Changed @ `{sha}`. Restarting in 2s…")
        ticket = {
            "channel_id": msg.channel.id,
            "message_id": msg.id,
            "user_id": itx.user.id,
            "sha": sha,
            "ts": time.time(),
        }
        try:
            with open(TICKET_PATH, "w") as f:
                json.dump(ticket, f)
        except Exception:
            log.exception("gagal menulis ticket restart; lanjut restart")

        await asyncio.sleep(2.0)
        await self._hard_restart()
async def setup(bot: commands.Bot):
    await bot.add_cog(RepoSlashSimple(bot))