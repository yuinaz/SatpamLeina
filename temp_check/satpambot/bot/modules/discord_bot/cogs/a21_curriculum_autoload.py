from __future__ import annotations
import logging
from discord.ext import commands
log = logging.getLogger(__name__)

class CurriculumAutoloadSafe(commands.Cog):
    """Safe Curriculum autoload that doesn't rely on a20._load_cfg()."""
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            log.info("[curriculum_autoload] safe tick")
        except Exception as e:
            log.debug("[curriculum_autoload] tick failed: %r", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(CurriculumAutoloadSafe(bot))
