import discord
from discord.ext import commands
from satpambot.bot.modules.discord_bot.ai.chatgpt_handler import call_ai

def setup_ai_commands(bot):
    @bot.command(name="ask", help="Tanyakan sesuatu ke AI")
    async def ask(ctx, *, question: str):
        await ctx.trigger_typing()
        response = await call_ai(question)
        await ctx.reply(response, mention_author=False)
