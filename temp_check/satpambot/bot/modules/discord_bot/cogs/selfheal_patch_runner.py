from __future__ import annotations

from discord.ext import commands
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import fnmatch
import discord

from satpambot.config.local_cfg import cfg
from satpambot.shared.selfheal_queue import list_tickets, update_ticket

ALLOW_GLOBS = ["satpambot/bot/modules/discord_bot/cogs/*.py"]

def _is_owner(bot: commands.Bot, user: discord.abc.User) -> bool:
    try:
        oid = int(cfg("OWNER_USER_ID", 0))
        return oid != 0 and int(user.id) == oid
    except Exception:
        return False

def _match_allowlist(path: Path) -> bool:
    s = path.as_posix()
    return any(fnmatch.fnmatch(s, g) for g in ALLOW_GLOBS)

def _apply_patch_ops(patch_ops: List[Dict[str, Any]], dry_run: bool = True) -> List[str]:
    logs = []
    for op in patch_ops:
        f = Path(op.get("file",""))
        find = op.get("find","")
        rep  = op.get("replace","")
        if not f.exists():
            logs.append(f"[SKIP] file not found: {f}")
            continue
        if not _match_allowlist(f):
            logs.append(f"[SKIP] not in allowlist: {f}")
            continue
        src = f.read_text(encoding="utf-8", errors="ignore")
        if find not in src:
            logs.append(f"[SKIP] pattern not found in {f}: {find[:100]}")
            continue
        nsrc = src.replace(find, rep, 1)
        if dry_run:
            logs.append(f"[DRY] would patch {f}")
        else:
            f.write_text(nsrc, encoding="utf-8")
            logs.append(f"[OK] patched {f}")
    return logs

async def _run_smoke() -> List[str]:
    cmds = [
        [ "python", "-m", "scripts.smoke_cogs" ],
        [ "python", "-m", "scripts.smoke_env" ],
    ]
    out = []
    for cmd in cmds:
        try:
            p = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            b = await p.communicate()
            out.append(f"$ {' '.join(cmd)}\n{b[0].decode('utf-8', errors='ignore')}")
        except Exception as e:
            out.append(f"$ {' '.join(cmd)}\n<failed: {e}>")
    return out

class SelfHealPatchRunner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_group(name="selfheal", description="Self-heal controls")
    async def selfheal(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.reply("subcommands: `queue`, `run <id> [apply]`")

    @selfheal.command(name="queue")
    async def selfheal_queue(self, ctx: commands.Context):
        if not _is_owner(self.bot, ctx.author):
            return await ctx.reply("Owner only.", delete_after=10)
        tickets = list_tickets()
        if not tickets:
            return await ctx.reply("Queue kosong.")
        emb = discord.Embed(title="Self-Heal Queue", colour=discord.Colour.blurple())
        for t in tickets[:10]:
            emb.add_field(name=t["id"], value=f"{t.get('level')} @ {t.get('where')}\nstatus: {t.get('status')}", inline=False)
        await ctx.reply(embed=emb)

    @selfheal.command(name="run")
    async def selfheal_run(self, ctx: commands.Context, ticket_id: str, apply: Optional[bool] = False):
        if not _is_owner(self.bot, ctx.author):
            return await ctx.reply("Owner only.", delete_after=10)
        tickets = list_tickets()
        t = next((x for x in tickets if x.get("id")==ticket_id), None)
        if not t:
            return await ctx.reply("Ticket tidak ditemukan.")
        diag = t.get("diagnosis") or {}
        patch_ops = diag.get("patch") or []
        dry = bool(cfg("SELFHEAL_DRY_RUN", True)) and (not apply)
        logs = _apply_patch_ops(patch_ops, dry_run=dry)
        smoke = await _run_smoke()
        update_ticket(ticket_id, status="applied" if not dry else "dry-run", logs={"apply": logs, "smoke": smoke})
        await ctx.reply(f"Ticket {ticket_id} {'applied' if not dry else 'dry-run'}.")
async def setup(bot: commands.Bot):
    await bot.add_cog(SelfHealPatchRunner(bot))