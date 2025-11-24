
# a00_strict_warning_filter_overlay.py (v7.4)
from discord.ext import commands
import os, warnings, logging

logger = logging.getLogger(__name__)
class StrictWarnFilter(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @commands.Cog.listener()
    async def on_ready(self):
        if os.getenv("STRICT_NO_WARN","1") != "1": return
        for cat in (DeprecationWarning, RuntimeWarning, ResourceWarning):
            warnings.filterwarnings("ignore", category=cat)
        logging.getLogger("discord.client").setLevel(logging.ERROR)
        logger.info("[warn-filter] STRICT_NO_WARN active")
async def setup(bot): 
    try: await bot.add_cog(StrictWarnFilter(bot))
    except Exception as e: logger.info("[warn-filter] setup swallowed: %r", e)