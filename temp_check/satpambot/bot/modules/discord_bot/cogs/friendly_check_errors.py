from __future__ import annotations

from discord.ext import commands

import logging

log = logging.getLogger(__name__)

TARGETS = {"tb", "testban", "ban"}

class FriendlyCheckErrors(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        try:
            name = getattr(getattr(ctx, 'command', None), 'qualified_name', '') or ''
            base = name.split(' ')[0] if name else ''
            if isinstance(error, commands.CheckFailure) and base in TARGETS:
                # Jangan raise — balas ramah dan log saja
                await ctx.reply("❌ Kamu tidak punya izin untuk perintah ini.", mention_author=False)
                log.info("[friendly_check] blocked %s by %s", name or "?", getattr(ctx.author,'id',None))
                return
        except Exception:
            pass  # jangan sampai error handler mematikan bot
async def setup(bot: commands.Bot):
    await bot.add_cog(FriendlyCheckErrors(bot))