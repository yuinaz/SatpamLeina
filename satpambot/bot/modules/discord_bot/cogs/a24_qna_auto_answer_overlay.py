from __future__ import annotations
import os, logging, re, asyncio
import discord
from discord.ext import commands
from satpambot.bot.modules.discord_bot.cogs.qna_dual_provider import QnaDualProvider

log = logging.getLogger(__name__)

# ---- Config (env) ----
def _ebool(k: str, d=False):
    v = os.getenv(k)
    if v is None or v == "":
        return d
    return str(v).lower() in ("1","true","yes","on")

QNA_DEBUG = _ebool("QNA_RUNTIME_DEBUG", False)
QNA_DETECT_PHRASE = os.getenv("QNA_DETECT_PHRASE", "Question by Leina")
QNA_DETECT_REGEX = os.getenv("QNA_DETECT_REGEX", r"(?i)^question\s+by\s+leina")
QNA_ANSWER_PREFIX = os.getenv("QNA_ANSWER_PREFIX", "Answer by")
QNA_DEDUP_CACHE = int(os.getenv("QNA_DEDUP_CACHE", "512") or "512")

_SMOKE_RX = re.compile(r"(^|\s)smoke:[0-9a-f]{6,}\b", re.I)

def _sanitize_question(text: str) -> str:
    # Remove smoke tokens and compress lines
    s = _SMOKE_RX.sub(" ", text or "")
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    return "\n".join(lines).strip()

def _title_matches(title: str) -> bool:
    if not title:
        return False
    t = (title or "").strip()
    if QNA_DETECT_PHRASE and QNA_DETECT_PHRASE.lower() in t.lower():
        return True
    try:
        if QNA_DETECT_REGEX and re.search(QNA_DETECT_REGEX, t):
            return True
    except Exception:
        pass
    return False

class QnaAutoAnswerOverlay(commands.Cog):
    """Runtime-safe QnA auto-answer.
    - Detects 'Question by Leina' on both on_message and on_message_edit.
    - Strict to QNA channel if QNA_CHANNEL_ID/LEARNING_QNA_CHANNEL_ID is set.
    - Sanitizes smoke tokens.
    - Idempotent (LRU of recent answered message IDs).
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.provider = QnaDualProvider(bot)
        self.qna_channel_id = int(os.getenv("QNA_CHANNEL_ID", os.getenv("LEARNING_QNA_CHANNEL_ID","0")) or 0)
        self._answered = []
        self._answered_set = set()

    # ---- Helpers ----
    def _in_qna(self, m: discord.Message) -> bool:
        if not self.qna_channel_id:
            return True
        ch_id = getattr(getattr(m, "channel", None), "id", None)
        return ch_id == self.qna_channel_id

    def _is_qna_question_embed(self, m: discord.Message) -> bool:
        try:
            if not getattr(m, "embeds", None):
                return False
            if not m.embeds:
                return False
            emb = m.embeds[0]
            title = (emb.title or "").strip()
            desc = (emb.description or "").strip()
            # title check (primary)
            if _title_matches(title):
                return True
            # heuristic backup: Indonesian prompt hint present
            if "Jawab ringkas" in desc or "jawab ringkas" in desc:
                return True
        except Exception:
            pass
        return False

    def _question_from_embed(self, m: discord.Message) -> str | None:
        try:
            emb = m.embeds[0]
            if emb.description:
                return emb.description
            if emb.fields:
                chunks = []
                for f in emb.fields:
                    if f and f.value:
                        chunks.append(str(f.value))
                return "\n".join(chunks) if chunks else None
        except Exception:
            return None
        return None

    def _dedup(self, msg_id: int) -> bool:
        if msg_id in self._answered_set:
            return True
        self._answered.append(msg_id)
        self._answered_set.add(msg_id)
        if len(self._answered) > QNA_DEDUP_CACHE:
            old = self._answered.pop(0)
            self._answered_set.discard(old)
        return False

    async def _answer(self, m: discord.Message):
        if self._dedup(m.id):
            return
        if not self._in_qna(m):
            if QNA_DEBUG:
                log.debug("[qna-auto] skip (not in qna) ch=%s id=%s", getattr(getattr(m,'channel',None),'id',None), m.id)
            return
        q = self._question_from_embed(m)
        if not q:
            return
        q = _sanitize_question(q)
        if QNA_DEBUG:
            log.debug("[qna-auto] answering id=%s by=%s q='%s'", m.id, getattr(m.author, 'id', None), q[:120])
        try:
            text, provider_name = await self.provider.aask(q)
            if not text:
                if QNA_DEBUG:
                    log.debug("[qna-auto] provider returned empty answer")
                return
            prov = provider_name or "Leina"
            emb = discord.Embed(title=f"{QNA_ANSWER_PREFIX} {prov}")
            emb.description = text
            try:
                emb.set_footer(text=f"provider={prov}")
            except Exception:
                pass
            try:
                await m.reply(embed=emb, mention_author=False)
            except Exception:
                await m.channel.send(embed=emb)
        except Exception:
            log.exception("[qna-auto] failed to answer")

    # ---- Events ----
    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        try:
            if not m.author.bot:
                return
            if not self._is_qna_question_embed(m):
                return
            # small delay to allow embed hydration on slow gateways
            await asyncio.sleep(0.15)
            await self._answer(m)
        except Exception:
            log.exception("[qna-auto] on_message error")

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        try:
            if not after.author.bot:
                return
            # Some gateways deliver embeds only after edit; handle here too.
            if not self._is_qna_question_embed(after):
                return
            await asyncio.sleep(0.05)
            await self._answer(after)
        except Exception:
            log.exception("[qna-auto] on_message_edit error")

async def setup(bot: commands.Bot):
    await bot.add_cog(QnaAutoAnswerOverlay(bot))
