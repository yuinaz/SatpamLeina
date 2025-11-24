# tests/test_discord_commands.py
import pytest
from discord.ext import commands

@pytest.mark.asyncio
async def test_ping_command():
    # Inisialisasi dummy bot
    bot = commands.Bot(command_prefix="!")
    
    @bot.command()
    async def ping(ctx):
        await ctx.send("Pong!")

    # Simulasikan konteks
    class DummyCtx:
        def __init__(self):
            self.sent = None
        async def send(self, msg):
            self.sent = msg
    
    ctx = DummyCtx()
    await ping.callback(ctx)
    assert ctx.sent == "Pong!"
