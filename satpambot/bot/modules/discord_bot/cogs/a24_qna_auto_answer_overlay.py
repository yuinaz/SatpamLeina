from __future__ import annotations
import os, logging
import discord
from discord.ext import commands
from satpambot.bot.modules.discord_bot.cogs.qna_dual_provider import QnaDualProvider
log = logging.getLogger(__name__)
QNA_EMBED_TITLE_LEINA = "Question by Leina"
def _env_bool(key: str, default: bool=False) -> bool:
    v = os.getenv(key)
    if v is None or v == "":
        return default
    return str(v).lower() in ("1","true","yes","on")
class QnaAutoAnswerOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enable = _env_bool("QNA_ENABLE", True)
        self.qna_channel_id = int(os.getenv("QNA_CHANNEL_ID", os.getenv("LEARNING_QNA_CHANNEL_ID","0")) or 0)
        self.dedup = set()
        self.provider = QnaDualProvider(bot)
    def _is_qna_question(self, m: discord.Message) -> bool:
        if not getattr(m, "embeds", None): return False
        if len(m.embeds) == 0: return False
        title = (m.embeds[0].title or "").strip()
        return title.startswith(QNA_EMBED_TITLE_LEINA)
    def _question_from_embed(self, m: discord.Message):
        try:
            emb = m.embeds[0]
            if emb.description: return emb.description
            if emb.fields:
                chunks = []
                for f in emb.fields:
                    if f and f.value: chunks.append(str(f.value))
                return "\n".join(chunks) if chunks else None
        except Exception: pass
        return None
    async def _answer_once(self, m: discord.Message):
        if m.id in self.dedup: return
        self.dedup.add(m.id)
        if not self.enable: return
        if self.qna_channel_id and getattr(getattr(m, "channel", None), "id", None) != self.qna_channel_id:
            return
        q = self._question_from_embed(m)
        if not q: return
        try:
            text, provider_name = await self.provider.aask(q)
            if not text: return
            prov = provider_name or "Leina"
            emb = discord.Embed(title=f"Answer by {prov}")
            emb.description = text
            try: await m.reply(embed=emb, mention_author=False)
            except Exception: await m.channel.send(embed=emb)
        except Exception: log.exception("[qna-auto-answer] failed to answer")
    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        try:
            if m.author.bot and self._is_qna_question(m):
                await self._answer_once(m)
        except Exception:
            log.exception("[qna-auto-answer] on_message error")
async def setup(bot: commands.Bot):
    await bot.add_cog(QnaAutoAnswerOverlay(bot))
