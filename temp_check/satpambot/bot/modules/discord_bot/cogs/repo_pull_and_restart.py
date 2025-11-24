from __future__ import annotations

from discord.ext import commands
import asyncio, os, sys
from pathlib import Path
from typing import Optional
import aiohttp
import discord
from discord import app_commands

def _owner_ids():
    raw = os.getenv("BOT_OWNER_IDS","") or os.getenv("OWNER_IDS","")
    ids=set()
    for p in raw.replace(";",
",").split(","):
        p=p.strip()
        if p.isdigit(): ids.add(int(p))
    one=os.getenv("OWNER_ID","").strip()
    if one.isdigit(): ids.add(int(one))
    return ids

def owner_or_admin_check():
    async def predicate(inter: discord.Interaction)->bool:
        if inter.user and inter.user.id in _owner_ids(): return True
        if isinstance(inter.user, discord.Member) and inter.user.guild_permissions.administrator: return True
        try: await inter.response.send_message("Perintah ini khusus **Owner/Admin**.", ephemeral=True)
        except Exception: pass
        return False
    return app_commands.check(predicate)

def _is_render_env()->bool:
    return bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID") or Path("/opt/render/project/src").exists())
def _repo_root()->Path: return Path(os.getenv("REPO_ROOT",".")).resolve()

async def _call_render_deploy_hook(hook:str):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(hook, json={"trigger":"discord:/repo_pull_and_restart"}) as r:
                txt = await r.text()
                return r.status<300, f"Render hook status **{r.status}**\n{txt[:1500]}"
    except Exception as e:
        return False, f"Hook error: {e}"

async def _git_pull(repo:Path, branch:str, hard_reset:bool):
    cmds=[["git","fetch","--all","-p"]]
    if hard_reset:
        cmds.append(["git","reset","--hard",f"origin/{branch}"])
    else:
        cmds.append(["git","checkout",branch])
        cmds.append(["git","pull","--ff-only","origin",branch])
    ok=True; outs=[]
    for c in cmds:
        try:
            p=await asyncio.create_subprocess_exec(*c,cwd=str(repo),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT)
            out=(await p.communicate())[0].decode("utf-8","ignore"); outs.append(f"$ {' '.join(c)}\n{out}")
            if p.returncode!=0: ok=False; break
        except Exception as e:
            outs.append(f"$ {' '.join(c)}\n[exception] {e}"); ok=False; break
    return ok, "\n\n".join(outs)[-1800:]

class RepoPullAndRestart(commands.Cog):
    def __init__(self, bot): self.bot=bot

    @app_commands.command(name="repo_pull_and_restart", description="Tarik update repo lalu restart proses (Render: panggil deploy hook)")
    @app_commands.describe(branch="Branch (default env GITHUB_BRANCH/main)", hard_reset="Paksa reset (local)", delay_restart="Delay detik (0-60)", mode="auto/local/render")
    @owner_or_admin_check()
    async def repo_pull_and_restart(self, inter:discord.Interaction, branch:Optional[str]=None, hard_reset:bool=False, delay_restart:app_commands.Range[int,0,60]=3, mode:str="auto"):
        await inter.response.defer(ephemeral=True,thinking=True)
        branch = branch or os.getenv("GITHUB_BRANCH","main")
        is_render = _is_render_env() if mode.lower()=="auto" else (mode.lower()=="render")
        if is_render:
            hook=os.getenv("RENDER_DEPLOY_HOOK_URL","").strip()
            if hook:
                ok,msg=await _call_render_deploy_hook(hook)
                await inter.followup.send(("✅ " if ok else "⚠️ ")+msg, ephemeral=True)
                return
        repo=_repo_root()
        if not (repo/".git").exists():
            await inter.followup.send(f"Tidak ada repo git di `{repo}`. Set `REPO_ROOT` jika perlu.", ephemeral=True); return
        ok,blob=await _git_pull(repo,branch,hard_reset)
        await inter.followup.send(("✅ Git OK\n" if ok else "⚠️ Git error\n")+f"```{blob}```",ephemeral=True)
        async def _do_exit():
            await asyncio.sleep(delay_restart)
            try: os._exit(0)
            except Exception: sys.exit(0)
        asyncio.create_task(_do_exit())
async def setup(bot):
    res = await bot.add_cog(RepoPullAndRestart(bot))
    import asyncio as _aio
    if _aio.iscoroutine(res): await res