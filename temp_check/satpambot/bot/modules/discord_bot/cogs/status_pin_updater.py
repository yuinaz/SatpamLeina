from __future__ import annotations

from discord.ext import commands

import asyncio
import discord

class StatusPinUpdater(commands.Cog):
    _started = False
    def __init__(self, bot: commands.Bot):
        self.bot = bot; self.interval_s = 900; self._last_payload = None; self._task = None
    def _render(self) -> str: return "SatpamBot is alive."
    async def _tick(self):
        payload = self._render()
        if payload == self._last_payload: return
        self._last_payload = payload
        # TODO: implement edit if you keep message IDs
    async def _loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try: await self._tick()
            except Exception: pass
            await asyncio.sleep(self.interval_s)
    @commands.Cog.listener()
    async def on_ready(self):
        if StatusPinUpdater._started: return
        StatusPinUpdater._started = True; self._task = asyncio.create_task(self._loop())
async def setup(bot: commands.Bot):
    await bot.add_cog(StatusPinUpdater(bot))