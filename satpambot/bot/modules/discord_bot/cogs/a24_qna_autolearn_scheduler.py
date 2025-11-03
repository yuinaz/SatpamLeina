
from __future__ import annotations
import os, json, logging, asyncio, random
from typing import Any, Dict, List, Optional, Tuple

try:
    from discord.ext import commands
except Exception as _e:  # loader-agnostic import guard
    commands = None  # type: ignore
    _IMPORT_ERR = _e
else:
    _IMPORT_ERR = None

log = logging.getLogger(__name__)

ENABLE = os.getenv("QNA_AUTOLEARN_ENABLE", "0") == "1"
TOPICS_PATH = os.getenv("QNA_TOPICS_PATH", "data/config/qna_topics.json")
PERIOD = int(os.getenv("QNA_AUTOLEARN_PERIOD_SEC", "180"))  # 3 menit per permintaan user
CHANNEL_ID = int(os.getenv("QNA_CHANNEL_ID", "0") or 0)     # channel isolasi untuk seed pertanyaan
TITLE_ISO = os.getenv("QNA_TITLE_ISOLATION", "Question by Leina")
TITLE_PUB = os.getenv("QNA_TITLE_PUBLIC", "Answer by Leina")

def _flatten_topics(data: Any) -> List[str]:
    topics: List[str] = []
    if isinstance(data, list):
        for x in data:
            if isinstance(x, str):
                s = x.strip()
                if s:
                    topics.append(s)
            elif isinstance(x, dict):
                q = x.get("q")
                if isinstance(q, str) and q.strip():
                    topics.append(q.strip())
    elif isinstance(data, dict):
        # dict-of-lists (kategori -> [pertanyaan])
        for _cat, arr in data.items():
            if not isinstance(arr, list):
                continue
            for x in arr:
                if isinstance(x, str) and x.strip():
                    topics.append(x.strip())
                elif isinstance(x, dict):
                    q = x.get("q")
                    if isinstance(q, str) and q.strip():
                        topics.append(q.strip())
    # normalize & dedupe
    seen = set(); out = []
    for t in topics:
        if t and t not in seen:
            seen.add(t); out.append(t)
    return out

def _load_topics() -> List[str]:
    try:
        with open(TOPICS_PATH, "r", encoding="utf-8") as f:
            js = json.load(f)
    except FileNotFoundError:
        log.warning("[qna-autolearn] topics file not found: %s", TOPICS_PATH)
        return []
    except Exception as e:
        log.warning("[qna-autolearn] topics file error: %r", e)
        return []
    items = _flatten_topics(js)
    if not isinstance(items, list) or not items:
        log.warning("[qna-autolearn] topics empty or invalid -> skip")
        return []
    log.info("[qna-autolearn] loaded %s topics from %s", len(items), TOPICS_PATH)
    return items

class QnAAutoLearnScheduler(commands.Cog):  # type: ignore[misc]
    def __init__(self, bot: Any):
        self.bot = bot
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self._topics: List[str] = []

    async def cog_load(self):
        if not ENABLE:
            log.info("[qna-autolearn] disabled")
            return
        self._topics = _load_topics()
        if not self._topics:
            log.warning("[qna-autolearn] topics empty -> skip run loop")
            return
        self._task = self.bot.loop.create_task(self._runner(), name="qna_autolearn")
        log.info("[qna-autolearn] started: %s topics | interval=%ss | chan=%s",
                 len(self._topics), PERIOD, CHANNEL_ID or "auto")

    async def cog_unload(self):
        if self._task and not self._task.done():
            self._stop.set()
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            log.info("[qna-autolearn] stopped")

    @commands.command(name="qna_topics")  # type: ignore[attr-defined]
    @commands.is_owner()                   # type: ignore[attr-defined]
    async def qna_topics_cmd(self, ctx: Any, sub: str="count"):
        if sub == "count":
            await ctx.reply(f"[qna-autolearn] topics={len(self._topics)}; file={TOPICS_PATH}")
            return
        if sub == "dump":
            sample = self._topics[:10]
            await ctx.reply("• " + "\n• ".join(sample) if sample else "(empty)")
            return
        await ctx.reply("usage: !qna_topics [count|dump]")

    async def _runner(self):
        # Small stagger to avoid clash with other schedulers
        await asyncio.sleep(5)
        idx = 0
        while not self._stop.is_set():
            try:
                if not self._topics:
                    self._topics = _load_topics()
                    if not self._topics:
                        await asyncio.sleep(PERIOD)
                        continue
                topic = self._topics[idx % len(self._topics)]
                await self._post_seed(topic)
                idx += 1
            except Exception:
                log.exception("[qna-autolearn] tick error")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=PERIOD)
            except asyncio.TimeoutError:
                pass

    async def _post_seed(self, topic: str):
        if not topic:
            return
        # Prefer isolation channel if provided; otherwise skip quietly
        if not CHANNEL_ID:
            log.warning("[qna-autolearn] CHANNEL_ID not set; skip post")
            return
        ch = await self._resolve_channel(CHANNEL_ID)
        if not ch:
            log.warning("[qna-autolearn] channel not found: %s", CHANNEL_ID)
            return
        # Simple seed embed (title uses isolation title)
        import discord
        emb = discord.Embed(title=TITLE_ISO, description=topic)
        await ch.send(embed=emb)
        log.info("[qna-autolearn] posted seed -> %s", topic[:80])

    async def _resolve_channel(self, ch_id: int):
        try:
            ch = self.bot.get_channel(ch_id)
            if ch:
                return ch
            return await self.bot.fetch_channel(ch_id)
        except Exception:
            return None

# loader-agnostic setup
async def setup(bot: Any):
    if _IMPORT_ERR is not None:
        raise _IMPORT_ERR
    await bot.add_cog(QnAAutoLearnScheduler(bot))  # type: ignore[attr-defined]

def setup(bot: Any):
    if _IMPORT_ERR is not None:
        raise _IMPORT_ERR
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(bot.add_cog(QnAAutoLearnScheduler(bot)))  # type: ignore[attr-defined]
            return
    except Exception:
        pass
    bot.add_cog(QnAAutoLearnScheduler(bot))  # type: ignore[attr-defined]
