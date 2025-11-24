from __future__ import annotations
import logging
import re
from discord.ext import commands
log = logging.getLogger(__name__)

def _cfg_str(k, d=""):
    try:
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_str
        return str(cfg_str(k, d))
    except Exception:
        return str(d)

XP_STR = _cfg_str("QNA_XP_PER_ANSWER_BOT", "25")
REASON = "qna-autolearn"

_ANS_PROVIDER = re.compile(r"^answer by (gemini|groq)", re.I)

class QnaAnswerAwardXP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, msg):
        try:
            if not getattr(msg, "embeds", None): return
            e = msg.embeds[0]
            ft = (getattr(getattr(e, "footer", None), "text", "") or "")
            if not _ANS_PROVIDER.search(ft): return  # only provider answers
            uid = getattr(getattr(msg, "author", None), "id", None)
            if uid is None: return
            # Dispatch XP (+25 by default). Bridge global will ignore due to reason "qna-..."
            try:
                self.bot.dispatch("xp_add", uid, int(XP_STR), REASON)
            except Exception:
                pass
            # Release WAIT gate so scheduler boleh post pertanyaan baru
            try:
                from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
                await UpstashClient().delete("qna:waiting")
            except Exception:
                pass
        except Exception as ex:
            log.warning("[qna-award] fail: %r", ex)

async def setup(bot):
    await bot.add_cog(QnaAnswerAwardXP(bot))
