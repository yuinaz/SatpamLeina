from discord.ext import commands
import discord

class Admin(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.has_permissions(ban_members=True)
    async def _disabled_unban(self, ctx, user_id: int):
        """Unban dinonaktifkan di Leina (gunakan Nixe)."""
        await ctx.reply("❌ Perintah unban dimatikan di Leina. Gunakan Nixe.", mention_author=False)

    @commands.has_permissions(manage_roles=True)
    @commands.command(name="buatrole")
    async def buatrole(self, ctx, *, name: str):
        role = await ctx.guild.create_role(name=name, reason=f"Create by {ctx.author}")
        await ctx.reply(f"✅ Role `{role.name}` dibuat", mention_author=False)

    @commands.has_permissions(manage_channels=True)
    @commands.command(name="buatchannel")
    async def buatchannel(self, ctx, *, name: str):
        ch = await ctx.guild.create_text_channel(name)
        await ctx.reply(f"✅ Channel `#{ch.name}` dibuat", mention_author=False)
async def setup(bot): await bot.add_cog(Admin(bot))