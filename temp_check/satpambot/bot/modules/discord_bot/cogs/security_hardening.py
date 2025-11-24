from __future__ import annotations

from discord.ext import commands

import os, time, asyncio
from collections import defaultdict, deque
import discord

# Simple in-memory cooldown for risky commands (by user)
_last_call = defaultdict(lambda: 0.0)
_window = float(os.getenv("RISK_CMD_COOLDOWN_SEC", "8"))  # default 8s

# Optional allowed guilds
_allowed_guild_ids = {int(x) for x in (os.getenv("ALLOWED_GUILD_IDS","").replace(';',',').split(',')) if x.strip().isdigit()}

RISKY = {"ban","testban","tb","tb_raw","unban"}

async def _enforce_policies(ctx: commands.Context):
    if not ctx.guild:
        raise commands.CheckFailure("Perintah hanya untuk dalam server.")
    if _allowed_guild_ids and ctx.guild.id not in _allowed_guild_ids:
        raise commands.CheckFailure("Server ini tidak diizinkan untuk bot ini.")
    name = ctx.command.qualified_name if ctx.command else ""
    if name in RISKY:
        now = time.time()
        key = (ctx.author.id, name)
        if now - _last_call[key] < _window:
            raise commands.CommandOnCooldown(commands.BucketType.user, _window - (now - _last_call[key]))
        _last_call[key] = now

class SecurityHardening(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        await _enforce_policies(ctx)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(f"⏱️ Tunggu {error.retry_after:.1f}s sebelum memakai perintah ini lagi.", mention_author=False)
        elif isinstance(error, commands.CheckFailure):
            await ctx.reply("❌ Kamu tidak diizinkan memakai perintah ini.", mention_author=False)
        else:
            # generic soft-fail
            try:
                await ctx.reply("⚠️ Terjadi kesalahan saat menjalankan perintah.", mention_author=False)
            except Exception:
                pass
async def setup(bot: commands.Bot):
    await bot.add_cog(SecurityHardening(bot))