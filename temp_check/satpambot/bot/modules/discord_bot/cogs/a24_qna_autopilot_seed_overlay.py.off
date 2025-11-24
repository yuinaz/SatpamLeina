from __future__ import annotations
import os, json, random, asyncio, logging, time
from typing import List, Optional
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

def _env_int(k: str, d: int) -> int:
    try: return int(os.getenv(k, str(d)))
    except Exception: return d

def _env_bool(k: str, d: bool=False) -> bool:
    v = os.getenv(k)
    if v is None: return d
    return str(v).strip().lower() in {"1","true","yes","on"}

def _cfg_qna_channel_id() -> int:
    for k in ("LEARNING_QNA_CHANNEL_ID","QNA_ISOLATION_CHANNEL_ID","QNA_CHANNEL_ID"):
        v = os.getenv(k)
        if v and str(v).isdigit(): return int(v)
    return 0

def _load_questions() -> List[str]:
    paths = [
        "data/config/qna_topics.json",
        "data/qna_topics.json",
    ]
    for p in paths:
        try:
            if os.path.exists(p):
                j = json.loads(open(p,"r",encoding="utf-8").read())
                if isinstance(j, list) and j:
                    return [str(x).strip() for x in j if str(x).strip()]
                if isinstance(j, dict) and "topics" in j:
                    arr = j.get("topics") or []
                    if isinstance(arr, list): 
                        return [str(x).strip() for x in arr if str(x).strip()]
        except Exception as e:
            log.warning("[qna-autopilot] load topics failed: %r", e)
    return ["Apa perbedaan RAM dan ROM?","Sebutkan contoh hewan mamalia."]

def _build_question_embed(q: str) -> discord.Embed:
    q = (q or "").strip()
    if len(q) > 1500:
        q = q[:1500] + "…"
    return discord.Embed(title="Question by Leina", description=q)

WAIT_KEY = "qna:waiting"
LAST_Q_KEY = "qna:last_question_id"

class _UpstashLite:
    def __init__(self):
        self.url = os.getenv("UPSTASH_REDIS_REST_URL")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        self.enabled = bool(self.url and self.token)
        self._mem = {}  # fallback if no upstash: key -> (expire_ts, value)

    async def get(self, key: str) -> Optional[str]:
        if self.enabled:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as s:
                    async with s.get(f"{self.url}/get/{key}", headers={"Authorization": f"Bearer {self.token}"} ) as r:
                        if r.status == 200:
                            j = await r.json()
                            return j.get("result")
            except Exception:
                return None
        exp, val = self._mem.get(key, (0,""))
        return val if exp >= time.time() else None

    async def setex(self, key: str, ttl_sec: int, value: str):
        if self.enabled:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as s:
                    async with s.get(f"{self.url}/setex/{key}/{ttl_sec}/{value}", headers={"Authorization": f"Bearer {self.token}"} ) as r:
                        _ = await r.text()
                        return
            except Exception:
                pass
        self._mem[key] = (time.time()+ttl_sec, value)

class QnaAutopilotSeedOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_id = _cfg_qna_channel_id()
        self.interval = _env_int("QNA_SEED_INTERVAL_SEC", 180)
        self.answer_timeout = _env_int("QNA_ANSWER_TIMEOUT_SEC", 180)
        self.enabled = _env_bool("QNA_AUTOPILOT_ENABLE", True) and _env_bool("QNA_ENABLE", True)
        self._qs = _load_questions()
        self.us = _UpstashLite()
        self._task: Optional[asyncio.Task] = None
        log.info("[qna-autopilot] loaded (interval=%ss, timeout=%ss, chan=%s)", self.interval, self.answer_timeout, self.channel_id)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.enabled:
            log.info("[qna-autopilot] disabled")
            return
        # create background loop safely (avoid create_task in __init__)
        if self._task is None or self._task.done():
            try:
                self._task = asyncio.create_task(self._loop(), name="qna_autopilot_loop")
                log.info("[qna-autopilot] started")
            except Exception as e:
                log.warning("[qna-autopilot] failed to start loop: %r", e)

    async def _loop(self):
        await self.bot.wait_until_ready()
        while not getattr(self.bot, "is_closed", lambda: False)():
            try:
                await self._emit_one()
            except Exception as e:
                log.warning("[qna-autopilot] tick error: %r", e)
            await asyncio.sleep(max(60, int(self.interval)))

    async def _emit_one(self):
        # re-resolve channel id each tick to pick up config changes
        if self.channel_id == 0:
            self.channel_id = _cfg_qna_channel_id()
        if not self.channel_id or not self.enabled:
            return
        # Only one question at a time
        try:
            if await self.us.get(WAIT_KEY) is not None:
                return
        except Exception:
            pass
        # resolve channel
        ch = self.bot.get_channel(self.channel_id)
        if ch is None:
            try:
                ch = await self.bot.fetch_channel(self.channel_id)
            except Exception as e:
                log.debug("[qna-autopilot] fetch_channel failed: %r", e)
                return
        # choose & send
        q = random.choice(self._qs)
        msg = None
        try:
            embed = _build_question_embed(q)
            msg = await ch.send(embed=embed)  # type: ignore
        except Exception as e:
            try:
                safe = (q or "").strip()
                if len(safe) > 1800: safe = safe[:1800] + "…"
                msg = await ch.send(f"**Question by Leina**\n{safe}")  # type: ignore
            except Exception as e2:
                log.warning("[qna-autopilot] send failed both embed and text: %r / %r", e, e2)
                return
        # set waiting gate with timeout
        try:
            await self.us.setex(WAIT_KEY, max(60, self.answer_timeout), "1")
            if msg and getattr(msg,"id",None):
                await self.us.setex(LAST_Q_KEY, max(24*3600, self.answer_timeout), str(msg.id))
        except Exception as e:
            log.debug("[qna-autopilot] setex failed: %r", e)

    async def cog_unload(self):
        try:
            if self._task:
                self._task.cancel()
        except Exception:
            pass

async def setup(bot: commands.Bot):
    # Avoid double-load if older version still registered
    try:
        old = bot.cogs.get("QnaAutopilotSeedOverlay")
        if old:
            bot.remove_cog("QnaAutopilotSeedOverlay")
    except Exception:
        pass
    await bot.add_cog(QnaAutopilotSeedOverlay(bot))
