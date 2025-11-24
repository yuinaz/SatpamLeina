from discord.ext import commands
import discord

import platform, psutil, datetime

class Info(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(name="status")
    async def status(self, ctx):
        mem = psutil.virtual_memory()
        uptime = datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(psutil.boot_time(), tz=datetime.timezone.utc).replace(tzinfo=None)
        embed = discord.Embed(title="Bot Status", color=discord.Color.blurple())
        embed.add_field(name="Python", value=platform.python_version())
        embed.add_field(name="discord.py", value=discord.__version__)
        embed.add_field(name="RAM", value=f"{mem.percent}%")
        embed.add_field(name="Uptime", value=str(uptime).split('.')[0], inline=False)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="botinfo")
    async def botinfo(self, ctx):
        guilds = len(self.bot.guilds)
        users = sum(g.member_count or 0 for g in self.bot.guilds)
        embed = discord.Embed(title="Bot Info", color=discord.Color.green())
        embed.add_field(name="Guilds", value=str(guilds))
        embed.add_field(name="Users", value=str(users))
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="servers")
    async def servers(self, ctx):
        names = ", ".join(g.name for g in self.bot.guilds[:20])
        await ctx.reply(f"Guilds: {names} {'...' if len(self.bot.guilds)>20 else ''}", mention_author=False)
async def setup(bot): await bot.add_cog(Info(bot))