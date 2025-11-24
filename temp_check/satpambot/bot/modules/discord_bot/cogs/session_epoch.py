from discord.ext import commands
import time, logging

log = logging.getLogger(__name__)

class SessionEpoch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        epoch = f"e{int(time.time())}"
        setattr(self.bot, "satpam_epoch", epoch)
        log.info("[epoch] session id set: %s", epoch)
async def setup(bot):
    await bot.add_cog(SessionEpoch(bot))