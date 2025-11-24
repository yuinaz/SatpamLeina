
import os
import logging
from discord.ext import commands

log = logging.getLogger(__name__)

class _QnaEnvNormalizer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._normalize()

    def _normalize(self):
        qna = os.getenv("QNA_CHANNEL_ID") or ""
        for k in ("QNA_ISOLATION_CHANNEL_ID", "LEARNING_QNA_CHANNEL_ID"):
            if not os.getenv(k) and qna:
                os.environ[k] = qna
                log.warning("[qna-env-normalizer] %s not set; mirroring from QNA_CHANNEL_ID=%s", k, qna)
        if not os.getenv("QNA_ISOLATION_COOLDOWN_SEC"):
            os.environ["QNA_ISOLATION_COOLDOWN_SEC"] = "180"
            log.warning("[qna-env-normalizer] default QNA_ISOLATION_COOLDOWN_SEC=180")

async def setup(bot):
    await bot.add_cog(_QnaEnvNormalizer(bot))
