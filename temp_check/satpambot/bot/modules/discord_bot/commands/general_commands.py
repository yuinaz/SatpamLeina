from discord.ext import commands

def register_general_commands(bot: commands.Bot):
    @bot.command(name="ping")
    async def ping(ctx: commands.Context):
        """Cek latency bot"""
        latency = round(bot.latency * 1000)
        await ctx.send(f"🏓 Pong! `{latency}ms`")
