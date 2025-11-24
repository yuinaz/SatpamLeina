from __future__ import annotations

from discord.ext import commands

# satpambot/bot/modules/discord_bot/cogs/uptime_probe.py
# Lightweight cog to track bot online/offline for /uptime route.
import discord

from satpambot.bot.helpers import uptime_state

class UptimeProbe(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        uptime_state.set_state(True)

    @commands.Cog.listener()
    async def on_connect(self):
        # Connected TCP, not yet READY; mark tentative online.
        uptime_state.set_state(True)

    @commands.Cog.listener()
    async def on_disconnect(self):
        uptime_state.set_state(False)
async def setup(bot: commands.Bot):
    await bot.add_cog(UptimeProbe(bot))