from discord.ext import commands
import os
import logging

log = logging.getLogger(__name__)

class SelfHealRuntime(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enabled = bool(os.getenv("SELFHEAL_ENABLE", "1") == "1") and bool(os.getenv("GROQ_API_KEY"))

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.enabled:
            log.warning("[self-heal] disabled (no GROQ_API_KEY or SELFHEAL_ENABLE=0)")
            return
        log.warning("[self-heal] SelfHealRuntime aktif (Groq)")
        # start tasks here if any (omitted for brevity)
async def setup(bot: commands.Bot):
    await bot.add_cog(SelfHealRuntime(bot))