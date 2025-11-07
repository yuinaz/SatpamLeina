from __future__ import annotations
import os, re, logging, asyncio
import discord
from discord.ext import commands
try:
    from satpambot.bot.modules.discord_bot.cogs.qna_dual_provider import QnaDualProvider
except Exception:
    class QnaDualProvider:  # type: ignore
        def __init__(self, bot): self.bot = bot
        async def aask(self, prompt: str): return (prompt or "", "Leina")
log = logging.getLogger(__name__)
_SMOKE_RX = re.compile(r'(^|\s)smoke:[0-9a-f]{6,}\b', re.I)
def _sanitize(text: str) -> str:
    s = _SMOKE_RX.sub(" ", text or "")
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    return "\n".join(lines).strip()
def _title_ok(t: str) -> bool:
    if not t: return False
    t = (t or "").lower().strip()
    return "question by leina" in t
class QnaAutoAnswerOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.provider = QnaDualProvider(bot)
        try: self.qna = int(os.getenv("QNA_CHANNEL_ID") or os.getenv("LEARNING_QNA_CHANNEL_ID") or "0")
        except Exception: self.qna = 0
        self._answered = set()
    def _is_qna_embed(self, m: discord.Message) -> bool:
        try:
            if not m.embeds: return False
            e = m.embeds[0]
            if _title_ok(getattr(e, "title", "") or ""): return True
            desc = (getattr(e, "description", "") or "").lower()
            return ("jawab ringkas" in desc) or ("jawab" in desc)
        except Exception: return False
    def _q(self, m: discord.Message):
        try:
            e = m.embeds[0]
            if e.description: return e.description
            if getattr(e, "fields", None):
                parts = [f.value for f in e.fields if getattr(f, "value", None)]
                if parts: return "\n".join(parts)
        except Exception: pass
        return None
    async def _answer(self, m: discord.Message):
        if m.id in self._answered: return
        self._answered.add(m.id)
        try:
            q = self._q(m)
            if not q: return
            q = _sanitize(q)
            text, prov = await self.provider.aask(q)
            if not text: return
            prov = prov or "Leina"
            emb = discord.Embed(title=f"Answer by {prov}", description=text)
            try: emb.set_footer(text=f"provider={prov}")
            except Exception: pass
            try: await m.reply(embed=emb, mention_author=False)
            except Exception: await m.channel.send(embed=emb)
        except asyncio.CancelledError: raise
        except Exception: log.exception("[qna-auto] answer failed")
    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        try:
            if not m.author.bot: return
            if self.qna and getattr(getattr(m, "channel", None), "id", None) != self.qna: return
            if not self._is_qna_embed(m): return
            await asyncio.sleep(0.05)
            await self._answer(m)
        except Exception: log.exception("[qna-auto] on_message error")
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        try:
            if not after.author.bot: return
            if self.qna and getattr(getattr(after, "channel", None), "id", None) != self.qna: return
            if not self._is_qna_embed(after): return
            await asyncio.sleep(0.02)
            await self._answer(after)
        except Exception: log.exception("[qna-auto] on_message_edit error")
async def setup(bot: commands.Bot):
    await bot.add_cog(QnaAutoAnswerOverlay(bot))
