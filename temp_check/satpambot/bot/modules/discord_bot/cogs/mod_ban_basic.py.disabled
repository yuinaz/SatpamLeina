# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import os
import re
from datetime import timedelta
from typing import Optional

import discord
from discord.ext import commands

DUR_RX = re.compile(r'^(?P<val>\d+)(?P<unit>[smhdw])$', re.I)

def parse_duration(s: str) -> Optional[int]:
    """Parse duration like 15m, 2h, 3d, 1w -> seconds."""
    m = DUR_RX.match(s.strip())
    if not m:
        return None
    val = int(m.group('val'))
    unit = m.group('unit').lower()
    mult = {'s':1, 'm':60, 'h':3600, 'd':86400, 'w':604800}[unit]
    return val * mult

async def try_get_log_channel(bot: commands.Bot) -> Optional[discord.abc.MessageableChannel]:
    # Try env LOG_CHANNEL_ID first
    log_id = os.getenv('LOG_CHANNEL_ID') or os.getenv('LOG_CHANNEL_ID_RAW')
    if log_id:
        try:
            ch = bot.get_channel(int(log_id))
            if ch:
                return ch
        except Exception:
            pass
    # Fall back to None (caller will just use ctx.channel)
    return None

class BasicBanCog(commands.Cog):
    """Minimal ban & tempban without touching any config.
    Commands:
      - !ban @user [reason?]
      - !tban @user <dur> [reason?]  (alias: !tempban)
    Supported dur units: s,m,h,d,w  (e.g., 10m, 2h, 3d)
    Notes:
      - Tempban unbans after duration using an in-memory task (won't survive restarts).
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._tasks: set[asyncio.Task] = set()

    # -------- helpers --------
    async def _log(self, ctx: commands.Context, text: str):
        ch = await try_get_log_channel(self.bot)
        try:
            if ch:
                await ch.send(text)
            else:
                await ctx.send(text)
        except Exception:
            # never crash due to logging
            pass

    # -------- commands --------
    @commands.command(name="ban", help="Ban member: !ban @user [reason?]")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban_cmd(self, ctx: commands.Context, member: discord.Member, *, reason: str = ""):
        try:
            await ctx.guild.ban(member, reason=reason or f"By {ctx.author} via !ban")
            await ctx.reply(f"✅ Banned {member.mention}" + (f" | alasan: {reason}" if reason else ""))
            await self._log(ctx, f"[BAN] {member} oleh {ctx.author} | alasan: {reason or '-'}")
        except discord.Forbidden:
            await ctx.reply("❌ Aku tidak punya izin untuk ban member itu (Forbidden).")
        except discord.HTTPException as e:
            await ctx.reply(f"❌ Gagal ban: {e}")

    @commands.command(name="tban", aliases=["tempban"], help="Tempban: !tban @user <dur> [reason?]  contoh: !tban @user 7d spam")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def tban_cmd(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = ""):
        seconds = parse_duration(duration)
        if not seconds:
            await ctx.reply("⚠️ Durasi tidak valid. Gunakan format seperti: 10m, 2h, 3d, 1w.")
            return
        try:
            await ctx.guild.ban(member, reason=reason or f"By {ctx.author} via !tban {duration}")
            await ctx.reply(f"✅ Tempbanned {member.mention} selama {duration}" + (f" | alasan: {reason}" if reason else ""))
            await self._log(ctx, f"[TBAN] {member} oleh {ctx.author} durasi {duration} | alasan: {reason or '-'}")
        except discord.Forbidden:
            await ctx.reply("❌ Aku tidak punya izin untuk ban member itu (Forbidden).")
            return
        except discord.HTTPException as e:
            await ctx.reply(f"❌ Gagal tempban: {e}")
            return

        async def _unban_later(guild: discord.Guild, user: discord.abc.User, delay: int):
            try:
                await asyncio.sleep(delay)
                await guild.unban(user, reason=f"Tempban selesai ({duration})")
                # Best-effort log
                ch = await try_get_log_channel(self.bot)
                try:
                    msg = f"[UNBAN] {user} selesai tempban {duration}"
                    if ch:
                        await ch.send(msg)
                except Exception:
                    pass
            except Exception:
                pass

        task = asyncio.create_task(_unban_later(ctx.guild, member, seconds))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

async def setup(bot: commands.Bot):
    await bot.add_cog(BasicBanCog(bot))