from discord.ext import commands
import discord

class Poll(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.has_permissions(manage_messages=True)
    @commands.command(name="poll")
    async def poll(self, ctx, *, question: str):
        msg = await ctx.send(f"📊 **Poll:** {question}\n✅ = Yes | ❌ = No")
        for e in ["✅","❌"]:
            await msg.add_reaction(e)

    @commands.has_permissions(manage_messages=True)
    @commands.command(name="closepoll")
    async def closepoll(self, ctx, message_id: int):
        try:
            msg = await ctx.channel.fetch_message(message_id)
            await msg.clear_reactions()
            await ctx.reply("🛑 Poll closed.", mention_author=False)
        except Exception:
            await ctx.reply("⚠️ Tidak bisa menemukan/menutup poll.", mention_author=False)
async def setup(bot): await bot.add_cog(Poll(bot))