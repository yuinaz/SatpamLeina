from discord.ext import commands
import logging

log = logging.getLogger("slash")
class SyncTools(commands.Cog):
    def __init__(self, bot): self.bot = bot
async def setup(bot):
    if any(ext.endswith('.cogs.slash_sync') for ext in getattr(bot, 'extensions', {}).keys()):
        log.info("[slash] synctools shim tidak dimuat (slash_sync sudah aktif)."); return
    await bot.add_cog(SyncTools(bot))