from discord.ext import commands
import logging

from satpambot.dashboard.discord_bridge import set_bot
log=logging.getLogger(__name__)
class LiveBridgeShim(commands.Cog):
    def __init__(self, bot):
        self.bot=bot
        try: set_bot(bot); log.info('[live_bridge_shim] set_bot on init')
        except Exception as e: log.warning('[live_bridge_shim] init failed: %s',e)
    @commands.Cog.listener()
    async def on_ready(self):
        try: set_bot(self.bot); log.info('[live_bridge_shim] set_bot on_ready')
        except Exception as e: log.warning('[live_bridge_shim] on_ready failed: %s',e)
async def setup(bot):
    await bot.add_cog(LiveBridgeShim(bot))
    log.info('[cogs_loader] loaded live_bridge_shim')