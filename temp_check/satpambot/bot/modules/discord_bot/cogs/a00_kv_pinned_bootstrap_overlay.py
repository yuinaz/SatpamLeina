import logging, os, asyncio
from discord.ext import commands
from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV

log = logging.getLogger(__name__)

class KVPinnedBootstrap(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.kv = PinnedJSONKV(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        # make sure message exists & pinned
        mid = await self.kv.ensure_ready()
        log.info("[kv-json] ready (msg_id=%s)", mid)

async def setup(bot: commands.Bot):
    await bot.add_cog(KVPinnedBootstrap(bot))
