from __future__ import annotations
import os, logging
from discord.ext import commands
log = logging.getLogger(__name__)
QNA_DEFAULT_ID = os.getenv("QNA_CHANNEL_ID_FORCE", "1426571542627614772")
class QnaChannelForceOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not os.getenv("QNA_CHANNEL_ID"):
            os.environ["QNA_CHANNEL_ID"] = QNA_DEFAULT_ID
            log.warning("[qna-force] QNA_CHANNEL_ID not set -> default=%s", QNA_DEFAULT_ID)
        # mirror to others if missing
        qna = os.getenv("QNA_CHANNEL_ID")
        for k in ("LEARNING_QNA_CHANNEL_ID","QNA_ISOLATION_CHANNEL_ID"):
            if not os.getenv(k):
                os.environ[k] = qna
                log.info("[qna-force] %s mirrored from QNA_CHANNEL_ID=%s", k, qna)
async def setup(bot): await bot.add_cog(QnaChannelForceOverlay(bot))
