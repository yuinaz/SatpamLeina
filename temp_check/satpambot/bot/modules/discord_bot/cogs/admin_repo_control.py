from __future__ import annotations

from discord.ext import commands

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import aiohttp
import discord
from discord import app_commands

LOG = __import__("logging").getLogger(__name__)

# --- helpers: permissions ---
def _owner_ids() -> set[int]:
    raw = os.getenv("BOT_OWNER_IDS", "") or os.getenv("OWNER_IDS", "")
    ids = set()
    for part in raw.replace(";",",").split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    # also allow single OWNER_ID
    oid = os.getenv("OWNER_ID", "").strip()
    if oid.isdigit():
        ids.add(int(oid))
    return ids

def _is_owner_or_admin(inter: discord.Interaction) -> bool:
    if inter.user and inter.user.id in _owner_ids():
        return True
    if isinstance(inter.user, discord.Member):
        return inter.user.guild_permissions.administrator
    return False

def owner_or_admin_check():
    async def predicate(inter: discord.Interaction) -> bool:
        if _is_owner_or_admin(inter):
            return True
        # ephemeral denial
        try:
            await inter.response.send_message("Kamu perlu **Administrator** atau **Owner** untuk perintah ini.", ephemeral=True)
        except Exception:
            pass
        return False
    return app_commands.check(predicate)

# --- helpers: env & detection ---
def _is_render_env() -> bool:
    root = os.getenv("RENDER", "") or os.getenv("RENDER_SERVICE_ID", "")
    if root:
        return True
    return Path("/opt/render/project/src").exists()

def _repo_root() -> Path:
    return Path(os.getenv("REPO_ROOT", ".")).resolve()

# --- the cog ---
class AdminRepoControl(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="repopull", description="Tarik update repo & (opsional) trigger redeploy (Render)")
    @app_commands.describe(
        branch="Nama branch (default: main)",
        hard_reset="Paksa reset ke origin/<branch> (local only)",
        mode="auto/local/render (default: auto)"
    )
    @owner_or_admin_check()
    async def repopull(
        self,
        inter: discord.Interaction,
        branch: str = "main",
        hard_reset: bool = False,
        mode: str = "auto",
    ):
        """
        - **Local/MiniPC**: git fetch/checkout/pull (opsional hard reset).
        - **Render**: POST ke `RENDER_DEPLOY_HOOK_URL` jika tersedia, atau arahkan user untuk manual deploy.
        """
        await inter.response.defer(ephemeral=True, thinking=True)

        is_render = _is_render_env() if mode.lower() == "auto" else (mode.lower() == "render")
        if is_render:
            hook = os.getenv("RENDER_DEPLOY_HOOK_URL", "").strip()
            if not hook:
                await inter.followup.send("Tidak ada `RENDER_DEPLOY_HOOK_URL`. Gunakan **Manual Deploy** di Render.", ephemeral=True)
                return
            try:
                async with aiohttp.ClientSession() as sess:
                    async with sess.post(hook, json={"trigger": "discord:/repopull"}) as resp:
                        text = await resp.text()
                        await inter.followup.send(f"Deploy hook dipanggil: **{resp.status}**\n```{text[:1500]}```", ephemeral=True)
                        return
            except Exception as e:
                await inter.followup.send(f"Gagal memanggil deploy hook: {e}", ephemeral=True)
                return

        # LOCAL path (or forced local)
        repo = _repo_root()
        if not (repo / ".git").exists():
            await inter.followup.send(f"Repo tidak ditemukan di `{repo}` (tidak ada .git). Set ENV `REPO_ROOT` jika perlu.", ephemeral=True)
            return

        cmds = []
        if hard_reset:
            cmds.append(["git","fetch","--all","-p"])
            cmds.append(["git","reset","--hard", f"origin/{branch}"])
        else:
            cmds.append(["git","fetch","--all","-p"])
            cmds.append(["git","checkout", branch])
            cmds.append(["git","pull","--ff-only","origin", branch])

        outs = []
        ok = True
        for cmd in cmds:
            try:
                p = await asyncio.create_subprocess_exec(*cmd, cwd=str(repo), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
                out = (await p.communicate())[0].decode("utf-8", errors="ignore")
                outs.append(f"$ {' '.join(cmd)}\n{out}")
                if p.returncode != 0:
                    ok = False
                    break
            except Exception as e:
                outs.append(f"$ {' '.join(cmd)}\n[exception] {e}")
                ok = False
                break

        msg = "✅ Git OK." if ok else "⚠️ Git error."
        blob = "\n\n".join(outs)
        if len(blob) > 1800:
            blob = blob[-1800:]
        await inter.followup.send(f"{msg}\n```{blob}```", ephemeral=True)

    @app_commands.command(name="restart", description="Restart proses bot (Render atau lokal)")
    @app_commands.describe(after_seconds="Delay sebelum restart (0-60 detik)")
    @owner_or_admin_check()
    async def restart(self, inter: discord.Interaction, after_seconds: app_commands.Range[int, 0, 60] = 3):
        await inter.response.send_message(f"Restarting dalam **{after_seconds}s**...", ephemeral=True)

        async def _do_exit():
            await asyncio.sleep(after_seconds)
            LOG.warning("[admin_repo_control] Exiting process by /restart command")
            # Try a graceful sys.exit first; if blocked, force
            try:
                os._exit(0)
            except Exception:
                sys.exit(0)

        asyncio.create_task(_do_exit())
async def setup(bot: commands.Bot):
    await bot.add_cog(AdminRepoControl(bot))