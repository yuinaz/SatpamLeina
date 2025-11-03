from discord.ext import commands
import os, logging, time, re
import discord

log = logging.getLogger(__name__)

# ==== ENV ====
ORDER = [s.strip() for s in (os.getenv("QNA_PROVIDER_ORDER", "groq,gemini")).split(",") if s.strip()]
PUBLIC_ID = int(os.getenv("QNA_PUBLIC_ID", "0") or 0)
ALLOWLIST_RAW = os.getenv("QNA_PUBLIC_ALLOWLIST", "")
PUBLIC_RATE_SEC = int(os.getenv("QNA_PUBLIC_RATE_SEC", "20"))
ISOLATION_ID = int(os.getenv("QNA_CHANNEL_ID", "0") or 0)

# Gate sources
ENV_PUBLIC_ENABLE = os.getenv("QNA_PUBLIC_ENABLE", "0") == "1"
UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
GATE_KEY = os.getenv("QNA_PUBLIC_GATE_KEY", "qna:public:enable")
GATE_CACHE_SEC = int(os.getenv("QNA_PUBLIC_GATE_CACHE_SEC","8"))

try:
    import httpx
except Exception:
    httpx = None

def _allowlist() -> set[int]:
    s = set()
    for tok in [t.strip() for t in ALLOWLIST_RAW.split(",") if t.strip()]:
        try: s.add(int(tok))
        except: pass
    if PUBLIC_ID: s.add(PUBLIC_ID)
    return s

ALLOW = _allowlist()

async def _upstash_get(client, key):
    if not (UPSTASH_URL and UPSTASH_TOKEN and client): return None
    try:
        r = await client.get(f"{UPSTASH_URL}/get/{key}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}, timeout=6.0)
        if r.status_code == 200:
            return (r.json() or {}).get("result")
    except Exception:
        pass
    return None

class PublicQnAReply(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_chan = {}
        self._client = httpx.AsyncClient() if httpx else None
        self._gate_cache_until = 0.0
        self._gate_cache_val = ENV_PUBLIC_ENABLE
        log.info("[qna-public] boot | allow=%s | rate=%ss | order=%s | env_enable=%s",
                 sorted(ALLOW) if ALLOW else "any", PUBLIC_RATE_SEC, ORDER, ENV_PUBLIC_ENABLE)

    def _is_allowed_channel(self, cid: int) -> bool:
        if ISOLATION_ID and cid == ISOLATION_ID:
            return False
        return (cid in ALLOW) if ALLOW else True

    def _throttle_ok(self, cid: int) -> bool:
        now = time.time()
        last = self._last_chan.get(cid, 0.0)
        if now - last < PUBLIC_RATE_SEC:
            return False
        self._last_chan[cid] = now
        return True

    async def _public_enabled(self) -> bool:
        # env flag OR upstash gate
        if ENV_PUBLIC_ENABLE:
            return True
        if not (self._client and UPSTASH_URL and UPSTASH_TOKEN):
            return False
        now = time.time()
        if now < self._gate_cache_until:
            return self._gate_cache_val
        val = await _upstash_get(self._client, GATE_KEY)
        self._gate_cache_val = (str(val) == "1")
        self._gate_cache_until = now + GATE_CACHE_SEC
        return self._gate_cache_val

    def _extract_query(self, msg: discord.Message) -> str:
        text = msg.content or ""
        if self.bot.user and self.bot.user.mention in text:
            text = text.replace(self.bot.user.mention, "").strip()
        text = re.sub(r'^\s*leina(chan)?[:,]?\s*', '', text, flags=re.I)
        return text.strip()

    async def _ask_llm(self, question: str):
        try:
            from ....providers.llm_facade import ask as llm_ask
        except Exception:
            llm_ask = None
        if not llm_ask:
            return None, None
        for prov in ORDER:
            try:
                model = os.getenv('GROQ_MODEL') if prov == 'groq' else os.getenv('GEMINI_MODEL')
                txt = await llm_ask(provider=prov, model=model,
                                    system='Jawab singkat, padat, aman, netral.',
                                    messages=[{'role':'user','content': question}],
                                    temperature=0.7, max_tokens=320)
                if txt and txt.strip():
                    return txt.strip(), prov.capitalize()
            except Exception:
                continue
        return None, None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not await self._public_enabled():
            return
        if not self._is_allowed_channel(message.channel.id):
            return
        content = message.content or ""
        has_mention = (self.bot.user and self.bot.user.mention in content)
        looks_pref = re.match(r'^\s*leina(chan)?\b', content, flags=re.I) is not None
        if not (has_mention or looks_pref):
            return
        if not self._throttle_ok(message.channel.id):
            return
        q = self._extract_query(message)
        if not q:
            return
        try:
            await message.channel.trigger_typing()
        except Exception:
            pass
        ans, prov = await self._ask_llm(q)
        if not ans:
            return
        emb = discord.Embed(title=f"Answer by {prov or 'Provider'}", description=ans)
        await message.channel.send(embed=emb)

async def setup(bot: commands.Bot):
    await bot.add_cog(PublicQnAReply(bot))
