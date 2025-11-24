from __future__ import annotations
import os, logging
from discord.ext import commands
log = logging.getLogger(__name__)
class QnaEnvDefaultPatchOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        qna = os.getenv("QNA_CHANNEL_ID")
        if qna:
            for k in ("QNA_ISOLATION_CHANNEL_ID","LEARNING_QNA_CHANNEL_ID"):
                if not os.getenv(k):
                    os.environ[k] = qna
                    log.warning("[qna-env-default] %s mirrored from QNA_CHANNEL_ID=%s", k, qna)
        if not os.getenv("QNA_ISOLATION_COOLDOWN_SEC"):
            os.environ["QNA_ISOLATION_COOLDOWN_SEC"] = "180"
            log.warning("[qna-env-default] default QNA_ISOLATION_COOLDOWN_SEC=180")
async def setup(bot): await bot.add_cog(QnaEnvDefaultPatchOverlay(bot))