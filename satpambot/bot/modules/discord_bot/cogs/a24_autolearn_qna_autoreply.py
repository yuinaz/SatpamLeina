from discord.ext import commands
import os, asyncio, logging, random, json, hashlib, time, re
import discord
from discord.ext import commands, tasks
from urllib.parse import quote as _q

try:
    import httpx
except Exception:
    httpx = None

log = logging.getLogger(__name__)

QNA_CHANNEL_ID = int(os.getenv("QNA_CHANNEL_ID") or 0) or 1426571542627614772
ASK_INTERVAL_MIN = int(os.getenv("QNA_AUTOASK_INTERVAL_MIN", "7"))
DEDUP_TTL_SEC = int(os.getenv("QNA_ASK_DEDUP_TTL_SEC", "259200"))
RECENT_MAX = int(os.getenv("QNA_ASK_RECENT_MAX", "200"))
QNA_TOPICS_FILE = os.getenv("QNA_TOPICS_FILE", "data/config/qna_topics.json")
QNA_TOPICS_JSON = os.getenv("QNA_TOPICS_JSON", "")
PROVIDER_ORDER = [s.strip() for s in (os.getenv("QNA_PROVIDER_ORDER") or "groq,gemini").split(",") if s.strip()]

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
UPSTASH_NS = os.getenv("QNA_ASK_DEDUP_NS", "qna:recent")

AUTOREPLY_SEED_ENABLE = os.getenv("QNA_AUTOREPLY_SEED_ENABLE", "0") == "1"
SEED_GATE_KEY = os.getenv("QNA_SEED_GATE_KEY", "qna:seed:gate")
SEED_GATE_TTL_SEC = int(os.getenv("QNA_SEED_GATE_TTL_SEC", "90"))

DEFAULT_POOLS = {
    "game": ["Bagaimana live-ops ala game Korea menjaga retensi tanpa terasa pay-to-win?"],
    "ai": ["Praktik aman memakai AI generatif dalam komunitas online?"],
    "musik": ["Bagaimana K-pop mendesain hook 15 detik yang efektif di short-video?"],
}

def _normalize(text: str) -> str:
    t = text.strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t

def _hash(text: str) -> str:
    return hashlib.sha1(_normalize(text).encode()).hexdigest()

async def _upstash_get(client, key):
    if not (UPSTASH_URL and UPSTASH_TOKEN and client): return None
    try:
        r = await client.get(f"{UPSTASH_URL}/get/{_q(key, safe='')}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}, timeout=8.0)
        if r.status_code == 200:
            return (r.json() or {}).get("result")
    except Exception:
        pass
    return None

async def _upstash_setex(client, key, ttl, val):
    if not (UPSTASH_URL and UPSTASH_TOKEN and client): return False
    try:
        r = await client.post(f"{UPSTASH_URL}/setex/{_q(key,safe='')}/{ttl}/{_q(val,safe='')}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}, timeout=8.0)
        return r.status_code == 200
    except Exception:
        return False

async def _llm_generate(topic: str) -> str:
    try:
        from ....providers.llm_facade import ask as llm_ask
    except Exception:
        llm_ask = None
    prompt = "Buat SATU pertanyaan singkat, sopan, netral, aman, berakhir '?'. Topik: " + topic
    if llm_ask:
        for prov in PROVIDER_ORDER:
            try:
                txt = await llm_ask(provider=prov, model=os.getenv('GROQ_MODEL') if prov=='groq' else os.getenv('GEMINI_MODEL'),
                                    system='Jawab satu kalimat tanya saja.', messages=[{'role':'user','content': prompt}],
                                    temperature=0.8, max_tokens=48)
                if txt and txt.strip().endswith('?') and len(_normalize(txt)) >= 12:
                    return txt.strip()
            except Exception:
                continue
    pool = DEFAULT_POOLS.get(topic, [])
    return random.choice(pool) if pool else "Apa yang sedang kamu pikirkan sekarang?"

class AutoAskQnA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recent = []
        self._client = httpx.AsyncClient() if httpx else None
        self.topics = self._load_topics()
        self._last_topic = None
        self._mem_gate_until = 0
        if AUTOREPLY_SEED_ENABLE:
            self.loop.start()
            log.info("[qna-autoask] enabled (interval=%s mnt, chan=%s)", ASK_INTERVAL_MIN, QNA_CHANNEL_ID)
        else:
            log.info("[qna-autoask] disabled by QNA_AUTOREPLY_SEED_ENABLE=0 (use scheduler as sole seeder)")

    def _load_topics(self):
        if QNA_TOPICS_FILE and os.path.exists(QNA_TOPICS_FILE):
            try:
                with open(QNA_TOPICS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and data:
                    return data
            except Exception as e:
                log.warning("[qna-autoask] cannot load topics file %s: %r", QNA_TOPICS_FILE, e)
        if QNA_TOPICS_JSON:
            try:
                data = json.loads(QNA_TOPICS_JSON)
                if isinstance(data, dict) and data:
                    return data
            except Exception as e:
                log.warning("[qna-autoask] invalid QNA_TOPICS_JSON: %r", e)
        return DEFAULT_POOLS

    def _remember(self, q: str):
        h = _hash(q)
        now = int(time.time())
        self.recent.append((h, now))
        self.recent = [(hh,ts) for hh,ts in self.recent if now-ts < DEDUP_TTL_SEC][-RECENT_MAX:]
        return h

    async def _seed_gate_active(self) -> bool:
        now = int(time.time())
        if now < self._mem_gate_until:
            return True
        if self._client and UPSTASH_URL and UPSTASH_TOKEN:
            try:
                val = await _upstash_get(self._client, SEED_GATE_KEY)
                if val is not None:
                    return True
            except Exception:
                pass
        return False

    async def _activate_seed_gate(self):
        until = int(time.time()) + SEED_GATE_TTL_SEC
        self._mem_gate_until = until
        if self._client and UPSTASH_URL and UPSTASH_TOKEN:
            try:
                await _upstash_setex(self._client, SEED_GATE_KEY, SEED_GATE_TTL_SEC, str(until))
            except Exception:
                pass

    def _pick_topic(self) -> str:
        keys = list(self.topics.keys())
        if not keys:
            return "global"
        if self._last_topic and len(keys) > 1 and self._last_topic in keys:
            alt = [k for k in keys if k != self._last_topic]
            topic = random.choice(alt)
        else:
            topic = random.choice(keys)
        self._last_topic = topic
        return topic

    @tasks.loop(minutes=ASK_INTERVAL_MIN)
    async def loop(self):
        if not AUTOREPLY_SEED_ENABLE:
            return
        try:
            ch = self.bot.get_channel(QNA_CHANNEL_ID)
            if not ch:
                log.warning("[qna-autoask] channel not found: %s", QNA_CHANNEL_ID)
                return
            if await self._seed_gate_active():
                log.debug("[qna-autoask] seed gate active; skip tick")
                return
            topic = self._pick_topic()
            q = await _llm_generate(topic)
            h = self._remember(q)
            if self._client and UPSTASH_URL and UPSTASH_TOKEN:
                await _upstash_setex(self._client, f"{UPSTASH_NS}:{h}", DEDUP_TTL_SEC, str(int(time.time())))
            await self._activate_seed_gate()
            emb = discord.Embed(title="Question by Leina", description=q)
            await ch.send(embed=emb)
            log.info("[qna-autoask] posted seed -> %s", q[:80])
        except Exception as e:
            log.warning("[qna-autoask] %r", e)

    @loop.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoAskQnA(bot))
