from __future__ import annotations

from discord.ext import commands

# modules/discord_bot/cogs/slash_basic.py
import asyncio
import discord

class SlashBasic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="ping", description="Cek latensi bot")
    async def ping(self, ctx: commands.Context):
        """Bisa slash (/ping) dan prefix (!ping/.ping)."""
        ms = round(self.bot.latency * 1000)
        if ctx.interaction:
            # acknowledge cepat biar ga timeout
            try:
                if not ctx.interaction.response.is_done():
                    await ctx.interaction.response.defer(ephemeral=True, thinking=False)
            except Exception:
                pass
            try:
                await ctx.interaction.followup.send(f"Pong! {ms}ms", ephemeral=True)
            except Exception:
                pass
        else:
            try:
                await ctx.reply(f"Pong! {ms}ms", mention_author=False)
            except Exception:
                await ctx.send(f"Pong! {ms}ms")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Diamkan CommandNotFound biar log tidak bising."""
        from discord.ext.commands import CommandNotFound
        if isinstance(error, CommandNotFound):
            return
        raise error
async def setup(bot: commands.Bot):
    await bot.add_cog(SlashBasic(bot))