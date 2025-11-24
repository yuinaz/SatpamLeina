from __future__ import annotations

from discord.ext import commands
import os, json, aiohttp
from pathlib import Path
from typing import Optional

from discord import app_commands
import discord

def _env_bool(n, d=False):
    v=os.getenv(n); 
    return d if v is None else str(v).strip().lower() in {"1","true","yes","on"}

GITHUB_SYNC_ENABLED=_env_bool("GITHUB_SYNC_ENABLED",True)
GITHUB_REPO=os.getenv("GITHUB_REPO","")
GITHUB_BRANCH=os.getenv("GITHUB_BRANCH","main")
GITHUB_BLACKLIST_TXT_PATH=os.getenv("GITHUB_BLACKLIST_TXT_PATH", os.getenv("GITHUB_BLACKLIST_TXT_P",""))
GITHUB_PATH_BLACKLIST_JSON=os.getenv("GITHUB_PATH_BLACKLIST_JSON","")
GITHUB_PATH_WHITELIST_JSON=os.getenv("GITHUB_PATH_WHITELIST_JSON","")
LOCAL_BLACKLIST_TXT=Path(os.getenv("LOCAL_BLACKLIST_TXT","satpambot/data/blacklist.txt"))
LOCAL_BLACKLIST_JSON=Path(os.getenv("LOCAL_BLACKLIST_JSON", GITHUB_PATH_BLACKLIST_JSON or "satpambot/data/blacklist.json"))
LOCAL_WHITELIST_JSON=Path(os.getenv("LOCAL_WHITELIST_JSON", GITHUB_PATH_WHITELIST_JSON or "satpambot/data/whitelist.json"))
GITHUB_TOKEN=os.getenv("GITHUB_TOKEN","").strip()

class GitHubSync(commands.Cog):
    def __init__(self, bot): self.bot=bot
    group=app_commands.Group(name="ghsync", description="Sinkronisasi GitHub")

    @group.command(name="status")
    async def status(self, inter:discord.Interaction):
        await inter.response.send_message("```json\n"+json.dumps({
            "enabled": GITHUB_SYNC_ENABLED,
            "repo": GITHUB_REPO, "branch": GITHUB_BRANCH,
            "remote": {"bltxt":GITHUB_BLACKLIST_TXT_PATH,"bljson":GITHUB_PATH_BLACKLIST_JSON,"wljson":GITHUB_PATH_WHITELIST_JSON},
            "local": {"bltxt":str(LOCAL_BLACKLIST_TXT),"bljson":str(LOCAL_BLACKLIST_JSON),"wljson":str(LOCAL_WHITELIST_JSON)},
            "auth": bool(GITHUB_TOKEN),
        }, indent=2, ensure_ascii=False)+"\n```", ephemeral=True)
async def setup(bot):
    import asyncio as _aio
    res = await bot.add_cog(GitHubSync(bot))
    if _aio.iscoroutine(res): await res