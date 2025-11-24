from __future__ import annotations

# cogs/gate_text_alias.py

from discord.ext import commands
import json
from pathlib import Path
import discord

from satpambot.config.local_cfg import cfg

LOCAL_PATH = Path(__file__).resolve().parents[5] / "local.json"

def _read_local() -> dict:
    try:
        return json.loads(LOCAL_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _write_local(update: dict) -> dict:
    base = _read_local()
    base.update(update or {})
    tmp = LOCAL_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(LOCAL_PATH)
    return base

def _is_owner(user: discord.abc.User) -> bool:
    try:
        return int(user.id) == int(cfg("OWNER_USER_ID") or 0)
    except Exception:
        return False

def _is_admin(member: discord.abc.User) -> bool:
    if isinstance(member, discord.Member):
        return member.guild_permissions.administrator
    return False

class GateTextAlias(commands.Cog):
    """Text alias for gate: !gate status|lock|unlock"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="gate")
    @commands.guild_only()
    async def gate(self, ctx: commands.Context, sub: str = "status"):
        sub = (sub or "status").lower().strip()
        if not (_is_owner(ctx.author) or _is_admin(ctx.author)):
            return await ctx.reply("❌ Hanya admin/owner yang boleh pakai perintah ini.", mention_author=False)

        if sub in ("status", "info"):
            data = _read_local()
            public = bool(data.get("PUBLIC_MODE_ENABLE", cfg("PUBLIC_MODE_ENABLE", False)))
            mentions = bool(data.get("CHAT_MENTIONS_ONLY", cfg("CHAT_MENTIONS_ONLY", True)))
            dm_mode = str(data.get("DM_MUZZLE", cfg("DM_MUZZLE", "log"))).lower()
            return await ctx.reply(
                f"**Public:** {'ON' if public else 'OFF'}\n"
                f"**Mentions-only:** {'ON' if mentions else 'OFF'}\n"
                f"**DM mode:** `{dm_mode}` (log/owner/off)",
                mention_author=False
            )

        if sub == "unlock":
            _write_local({"PUBLIC_MODE_ENABLE": True})
            return await ctx.reply("✅ Gate dibuka (PUBLIC_MODE_ENABLE = true).", mention_author=False)

        if sub == "lock":
            _write_local({"PUBLIC_MODE_ENABLE": False})
            return await ctx.reply("🔒 Gate dikunci (PUBLIC_MODE_ENABLE = false).", mention_author=False)

        return await ctx.reply("Format: `!gate status` | `!gate lock` | `!gate unlock`", mention_author=False)
async def setup(bot: commands.Bot):
    await bot.add_cog(GateTextAlias(bot))