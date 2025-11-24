
from discord.ext import commands
class _PermGuard(commands.Cog):
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CheckFailure):
            try: await ctx.reply(f"⚠️ {error}", mention_author=False)
            except Exception: pass
async def setup(bot): await bot.add_cog(_PermGuard())