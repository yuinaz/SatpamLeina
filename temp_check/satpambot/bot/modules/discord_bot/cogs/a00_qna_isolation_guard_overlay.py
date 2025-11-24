from __future__ import annotations
import os, logging
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

def _env_bool(k: str, default: bool=False) -> bool:
    v = os.getenv(k)
    if v is None or v == "":
        return default
    return str(v).lower() in ("1","true","yes","on")

class QnaIsolationGuard(commands.Cog):
    """Hard-guard: di channel QNA isolasi hanya bot yang boleh bicara.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enable = _env_bool("QNA_ISOLATION_STRICT", True)
        self.qna_channel_id = int(os.getenv("QNA_CHANNEL_ID", os.getenv("LEARNING_QNA_CHANNEL_ID","0")) or 0)
        self.redirect_id = int(os.getenv("QNA_REDIRECT_CHANNEL_ID","0") or 0)
        self.silent_delete = _env_bool("QNA_DELETE_SILENT", True)
        log.info("[qna-guard] enable=%s qna_channel_id=%s redirect=%s silent=%s",
                 self.enable, self.qna_channel_id, self.redirect_id, self.silent_delete)

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if not self.enable or self.qna_channel_id == 0:
            return
        try:
            ch = getattr(m, "channel", None)
            if not ch or getattr(ch, "id", None) != self.qna_channel_id:
                return
            # Allow only bot messages in QnA isolasi
            if getattr(m, "author", None) and getattr(m.author, "bot", False):
                return
            # Delete user message (best effort)
            try:
                await m.delete()
            except Exception:
                pass
            if not self.silent_delete and self.redirect_id:
                try:
                    dest = await self.bot.fetch_channel(self.redirect_id)
                    await dest.send(f"<@{m.author.id}>, QnA isolasi hanya untuk Leina ⇄ Provider. Silakan tanya di channel yang benar.")
                except Exception:
                    pass
        except Exception:
            log.exception("[qna-guard] error")

async def setup(bot: commands.Bot):
    await bot.add_cog(QnaIsolationGuard(bot))
