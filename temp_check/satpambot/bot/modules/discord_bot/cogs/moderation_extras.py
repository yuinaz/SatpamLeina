from discord.ext import commands
import discord

class ModerationExtras(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sbdiag")
    async def sbdiag(self, ctx: commands.Context):
        try:
            exts = sorted(self.bot.extensions.keys())
            await ctx.send("Diag OK. Loaded extensions: " + ", ".join(exts))
        except Exception as e:
            await ctx.send(f"Diag error: {e}")
async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationExtras(bot))