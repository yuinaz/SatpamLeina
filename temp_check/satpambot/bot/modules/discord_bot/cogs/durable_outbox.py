from discord.ext import commands
import logging

from ..helpers.send_queue import SendQueue

log = logging.getLogger(__name__)

class DurableOutbox(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.q = SendQueue(bot)

    async def cog_load(self):
        await self.q.start()

    async def cog_unload(self):
        await self.q.stop()

    async def send(self, channel_id: int, **kwargs):
        await self.q.enqueue(channel_id, **kwargs)
async def setup(bot):
    await bot.add_cog(DurableOutbox(bot))