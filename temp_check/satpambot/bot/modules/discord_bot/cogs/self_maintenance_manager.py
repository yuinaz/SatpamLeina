from __future__ import annotations

from discord.ext import commands

import asyncio
import discord
from discord.ext import tasks
from .selfheal_router import send_selfheal

def _mk(title, desc, color=0x2ecc71): return discord.Embed(title=title, description=desc, color=color)

class SelfMaintenanceManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.unloaded = []
        if hasattr(self,'loop'): self.loop.start()  # type: ignore

    async def _maybe_await(self, result):
        if hasattr(result, '__await__'):
            return await result
        return result

    @tasks.loop(minutes=30)
    async def loop(self):
        await send_selfheal(self.bot, _mk('Maintenance', 'Heartbeat ok'))
        for ext in []:
            try:
                await self._maybe_await(self.bot.unload_extension(ext)); self.unloaded.append(ext)
            except Exception: pass
            try:
                await self._maybe_await(self.bot.load_extension(ext))
            except Exception: pass
async def setup(bot): await bot.add_cog(SelfMaintenanceManager(bot))