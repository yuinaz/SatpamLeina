from discord.ext import commands

import asyncio

class XpBridgeSoftRetry(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        loop = getattr(bot, "loop", None) or asyncio.get_running_loop()
        self._task = loop.create_task(self._runner())

    async def _runner(self):
        await asyncio.sleep(0)

async def setup(bot):
    await bot.add_cog(XpBridgeSoftRetry(bot))