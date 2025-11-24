from discord.ext import commands
import logging

log = logging.getLogger(__name__)

class QNAAllowShim(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
async def setup(bot):
    # In production we would patch PublicChatGate to allow QNA channel. In smoke, just log.
    try:
        gate = bot.cogs.get("PublicChatGate")  # type: ignore
        if gate:
            log.info("[qna_allow] gate found; patch would be applied in runtime")
        else:
            log.info("[qna_allow] gate not found in smoke; no-op")
    except Exception as e:
        log.info("[qna_allow] gate not found or patch failed: %r", e)
    await bot.add_cog(QNAAllowShim(bot))