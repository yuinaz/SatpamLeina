
from discord.ext import commands
import os, asyncio, random, time, re, hashlib
import discord

import httpx

QNA_CH_ID = int(os.getenv("QNA_CHANNEL_ID","0") or "0")
ENABLE = os.getenv("QNA_AUTOPILOT","1") == "1"
MIN_SEC = int(os.getenv("QNA_INTERVAL_MIN","120"))
MAX_SEC = int(os.getenv("QNA_INTERVAL_MAX","420"))
UP_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UP_TOK = os.getenv("UPSTASH_REDIS_REST_TOKEN")
DEDUP_WINDOW_SEC = int(os.getenv("QNA_DEDUP_SEC","21600"))

def norm(s:str)->str:
    return re.sub(r"\s+"," ", re.sub(r"[^\w\s]","", (s or "").lower())).strip()

def qhash(s:str)->str:
    return hashlib.sha1(norm(s).encode()).hexdigest()

async def upstash(cmd:list[str]):
    if not (UP_URL and UP_TOK): return None
    headers = {"Authorization": f"Bearer {UP_TOK}", "Content-Type":"application/json"}
    async with httpx.AsyncClient(timeout=10) as x:
        r = await x.post(UP_URL, headers=headers, json=cmd)
        r.raise_for_status()
        j = r.json()
        return j.get("result")

PROMPT_SEED = (
    "Bangun 1 pertanyaan baru, unik, bernilai belajar, topik bebas (tekno, coding, keamanan siber, jaringan, Python, Discord bot, atau praktik DevOps). "
    "Hanya keluarkan pertanyaan SATU BARIS tanpa jawaban. Hindari pertanyaan yang pernah muncul 6 jam terakhir."
)

class QnaAutopilot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._task = None

    async def cog_load(self):
        if ENABLE and QNA_CH_ID:
            self._task = asyncio.create_task(self._loop())

    async def _loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                ch = self.bot.get_channel(QNA_CH_ID)
                if ch is None:
                    await asyncio.sleep(30); continue

                # mintakan 1 pertanyaan
                try:
                    res = await self.bot.llm_ask(PROMPT_SEED, system="Tugasmu hanya memunculkan pertanyaan satu baris.")
                    question = res["text"].splitlines()[0].strip()
                except Exception:
                    await asyncio.sleep(60); continue

                if not question or len(norm(question)) < 8:
                    await asyncio.sleep(30); continue

                # dedup via Upstash (hindari pengulangan Q)
                h = qhash(question)
                now = int(time.time())
                try:
                    await upstash(["ZREMRANGEBYSCORE","qna:asked","-inf", str(now-DEDUP_WINDOW_SEC)])
                    exists = await upstash(["ZSCORE","qna:asked", h])
                    if exists is None:
                        await upstash(["ZADD","qna:asked", str(now), h])
                    else:
                        await asyncio.sleep(random.randint(MIN_SEC, MAX_SEC))
                        continue
                except Exception:
                    pass

                # kirim Q sebagai embed (agar autoreply menangkapnya)
                eq = discord.Embed(title="Q · Leina", description=question)
                await ch.send(embed=eq)

            except Exception:
                await asyncio.sleep(20)

            await asyncio.sleep(random.randint(MIN_SEC, MAX_SEC))
async def setup(bot):
    await bot.add_cog(QnaAutopilot(bot))