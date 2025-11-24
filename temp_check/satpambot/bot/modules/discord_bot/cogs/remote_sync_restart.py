from __future__ import annotations

from discord.ext import commands

# remote_sync_restart.py — hardened /repo (NO-ENV)
import asyncio, json, os, sys, io, zipfile, logging, aiohttp
from pathlib import Path
from typing import Dict, Any, List
import discord

from discord import app_commands
from satpambot.bot.modules.discord_bot.helpers import restart_guard as rg

log = logging.getLogger(__name__)
ACK_DELAY = 2.0

def _reexec_inplace():
    os.execv(sys.executable, [sys.executable, *sys.argv])

def _load_cfg() -> Dict[str, Any]:
    p = Path("config") / "remote_sync.json"
    try: return json.loads(p.read_text("utf-8"))
    except Exception:
        return {"archive": "", "repo_root_prefix": "", "pull_sets": [
            {"include": ["config/"], "allow_exts": ["json","txt","yaml","yml"]},
            {"include": ["satpambot/"], "allow_exts": ["py"]},
        ], "files": [], "timeout_s": 20}

async def _fetch_bytes(url: str, timeout: int) -> bytes:
    async with aiohttp.ClientSession() as s:
        async with s.get(url, timeout=timeout) as r:
            r.raise_for_status(); return await r.read()

def _should_include(name: str, cfg: Dict[str, Any]) -> bool:
    pulls = cfg.get("pull_sets") or []
    name_l = name.lower()
    for rule in pulls:
        inc = rule.get("include") or []
        exts = [e.lower() for e in (rule.get("allow_exts") or [])]
        if inc and not any(name.startswith(i) for i in inc): continue
        if exts and not any(name_l.endswith("." + e) for e in exts): continue
        return True
    return False

def _apply_archive_bytes(data: bytes, cfg: Dict[str, Any]) -> List[str]:
    root_prefix = (cfg.get("repo_root_prefix") or "").strip()
    changed: List[str] = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if info.is_dir(): continue
            name = info.filename
            rel = name[len(root_prefix):] if root_prefix and name.startswith(root_prefix) else name
            if not _should_include(rel, cfg): continue
            target = Path(rel); target.parent.mkdir(parents=True, exist_ok=True)
            new_bytes = z.read(info)
            if target.exists():
                try:
                    if target.read_bytes() == new_bytes: continue
                except Exception: pass
            target.write_bytes(new_bytes); changed.append(rel)
    return changed

async def _pull_archive_and_apply() -> List[str]:
    cfg = _load_cfg(); url = cfg.get("archive")
    if not url: return []
    data = await _fetch_bytes(url, int(cfg.get("timeout_s", 20)))
    return _apply_archive_bytes(data, cfg)

class RemoteSyncRestart(commands.Cog):
    def __init__(self, bot): self.bot = bot
    group = app_commands.Group(name="repo", description="Repo ops (ZIP-friendly)")
    group_rt = app_commands.Group(name="runtime", description="Runtime ops")

    @group.command(name="pull")
    async def pull(self, itx: discord.Interaction):
        await itx.response.defer(ephemeral=True, thinking=True)
        changed = await _pull_archive_and_apply()
        await itx.followup.send(f"✅ Changed: {len(changed)} file(s).", ephemeral=True)

    @group.command(name="pull_and_restart")
    async def pull_and_restart(self, itx: discord.Interaction):
        await itx.response.defer(ephemeral=True, thinking=True)
        ok, age = rg.should_restart()
        if not ok:
            return await itx.followup.send(f"⏱️ Restart triggered {int(age or 0)}s ago — skipped.", ephemeral=True)
        changed = await _pull_archive_and_apply()
        rg.mark("pull_and_restart")
        await itx.followup.send(f"✅ Changed: {len(changed)}. Restarting in {ACK_DELAY:.1f}s…", ephemeral=True)
        async def _delay():
            try: await asyncio.sleep(ACK_DELAY)
            except Exception: pass
            _reexec_inplace()
        asyncio.create_task(_delay())

    @group_rt.command(name="restart")
    async def rt_restart(self, itx: discord.Interaction):
        await itx.response.send_message(f"🔁 Restarting in {ACK_DELAY:.1f}s…", ephemeral=True)
        async def _d(): 
            try: await asyncio.sleep(ACK_DELAY)
            except Exception: pass
            _reexec_inplace()
        asyncio.create_task(_d())

async def _sync_all_guilds_once(bot: commands.Bot):
    await bot.wait_until_ready()
    try:
        for g in bot.guilds:
            try: await bot.tree.sync(guild=g)
            except Exception: pass
    except Exception: pass
async def setup(bot: commands.Bot):
    cog = RemoteSyncRestart(bot)
    await bot.add_cog(cog)
    # Register as the authoritative /repo (override any earlier)
    bot.tree.add_command(cog.group, override=True)
    bot.tree.add_command(cog.group_rt, override=True)
    asyncio.create_task(_sync_all_guilds_once(bot))