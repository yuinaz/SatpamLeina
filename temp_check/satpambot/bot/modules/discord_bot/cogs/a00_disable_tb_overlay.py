from __future__ import annotations

# a00_disable_tb_overlay.py

from discord.ext import commands

try:
    from discord import app_commands
except Exception:
    app_commands = None

DISABLED = {"tb","testban"}

class DisableTB(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _remove_text(self):
        for name in list(DISABLED):
            if self.bot.get_command(name):
                self.bot.remove_command(name)

    async def _remove_slash(self):
        if not app_commands: return
        for cmd in list(self.bot.tree.get_commands() or []):
            if cmd.name in DISABLED:
                self.bot.tree.remove_command(cmd.name, type=None)
        try:
            await self.bot.tree.sync()
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        try: await self._remove_text()
        except Exception: pass
        try: await self._remove_slash()
        except Exception: pass

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        if ctx.command and ctx.command.name in DISABLED:
            await ctx.reply("❌ Perintah **tb/testban** dimatikan di Leina. Gunakan **Nixe** untuk moderasi.", mention_author=False)
            raise commands.CheckFailure("tb disabled")
async def setup(bot: commands.Bot):
    await bot.add_cog(DisableTB(bot))