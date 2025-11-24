from discord.ext import commands
from satpambot.bot.modules.discord_bot.utils.notifier import format_log_message

def register_debug_commands(bot: commands.Bot):
    @bot.command(name="status")
    async def status(ctx: commands.Context):
        """Cek status bot"""
        await ctx.send("✅ Bot aktif dan berjalan.")

    @bot.command(name="log")
    async def log(ctx: commands.Context, *, reason: str):
        """Simulasi logging"""
        log_msg = format_log_message(ctx.author, reason)
        await ctx.send(f"📝 Log: `{log_msg}`")

    @bot.command(name="test")
    async def test(ctx: commands.Context):
        """Command untuk testing"""
        await ctx.send("✅ Bot dalam kondisi baik.")
