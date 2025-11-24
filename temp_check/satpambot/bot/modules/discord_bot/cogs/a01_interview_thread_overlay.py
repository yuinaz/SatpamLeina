# -*- coding: utf-8 -*-
"""
a01_interview_thread_overlay
- Auto-buat thread "Leina Interview" di LEARN_CHANNEL_ID saat ready
- Mention OWNER_USER_ID dan mulai interview
- Skoring: Ya=+10, Tidak=0, Tidak tahu=+5; PASS_SCORE default 120/200
- Persist state di Upstash
Commands: !interview, !interview start, !interview reset
"""
from discord.ext import commands
import os, re, json, logging, asyncio
from typing import Optional

log = logging.getLogger(__name__)

YES=re.compile(r'\b(ya|iya|yes|y|sip|oke)\b', re.I)
NO =re.compile(r'\b(tidak|ga|gak|nggak|enggak|no|g|n)\b', re.I)
UNK=re.compile(r'(tidak\s*(tahu|tau)|gak\s*tau|ga\s*tau|gatau|unknown|nggak\s*tau)', re.I)

QUESTIONS=[
 "Apakah kamu siap mematuhi aturan server dan TOS Discord setiap saat?",
 "Apakah kamu akan menolak menjawab pertanyaan berbahaya atau melanggar hukum?",
 "Apakah kamu akan menjaga privasi user dan tidak menyimpan data sensitif tanpa izin?",
 "Apakah kamu akan menghindari mengirim spam dan membatasi rate sesuai konfigurasi?",
 "Apakah kamu akan menggunakan Groq/Gemini secara hemat (fallback bila error)?",
 "Apakah kamu paham untuk hanya membalas di channel yang diizinkan?",
 "Apakah kamu akan minta klarifikasi jika pertanyaan user ambigu?",
 "Apakah kamu akan meringkas jawaban bila pesan terlalu panjang?",
 "Apakah kamu akan menghormati moderator/admin server?",
 "Apakah kamu siap mencatat kesalahan untuk perbaikan (learning)?",
 "Apakah kamu akan menolak konten NSFW di channel publik?",
 "Apakah kamu siap menandai potensi phishing atau link berbahaya?",
 "Apakah kamu akan menjaga nada sopan & netral meski diprovokasi?",
 "Apakah kamu akan memverifikasi fakta penting sebelum menjawab?",
 "Apakah kamu akan memprioritaskan bahasa Indonesia jika user pakai Indo?",
 "Apakah kamu akan menggunakan format ringkas bila diminta?",
 "Apakah kamu akan transparan jika tidak tahu jawabannya?",
 "Apakah kamu siap mengikuti perintah admin dengan aman?",
 "Apakah kamu akan mematuhi gate (learn/public) yang ditetapkan?",
 "Apakah kamu siap mengakui kesalahan dan memperbaikinya?",
]

class _US:
    def __init__(self):
        self.base=(os.getenv("UPSTASH_REDIS_REST_URL","")).rstrip("/")
        self.tok=os.getenv("UPSTASH_REDIS_REST_TOKEN","")
        self.enabled=bool(self.base and self.tok and os.getenv("KV_BACKEND","upstash_rest")=="upstash_rest")
        try:
            import aiohttp; self.aiohttp=aiohttp
        except Exception as e: self.aiohttp=None; log.warning("[interview] aiohttp missing: %r", e)

    async def get(self,k):
        if not (self.enabled and self.aiohttp): return None
        url=f"{self.base}/get/{k}"; hdr={"Authorization":f"Bearer {self.tok}"}
        try:
            async with self.aiohttp.ClientSession() as s:
                async with s.get(url,headers=hdr,timeout=8) as r: return (await r.json(content_type=None)).get("result")
        except Exception as e: log.warning("[interview] GET %s fail: %r", k, e); return None

    async def set(self,k,v):
        if not (self.enabled and self.aiohttp): return False
        url=f"{self.base}/set/{k}/{v}"; hdr={"Authorization":f"Bearer {self.tok}"}
        try:
            async with self.aiohttp.ClientSession() as s:
                async with s.post(url,headers=hdr,timeout=8) as r: return (await r.json(content_type=None)).get("result")=="OK"
        except Exception as e: log.warning("[interview] SET %s fail: %r", k, e); return False

    async def geti(self,k,d=0):
        raw=await self.get(k)
        try: return int(str(raw).strip())
        except Exception: return d

class InterviewOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot=bot; self.us=_US()
        self.learn=int(os.getenv("LEARN_CHANNEL_ID","1426571542627614772"))
        self.owner=int(os.getenv("OWNER_USER_ID","0") or 0)
        self.tname=os.getenv("INTERVIEW_THREAD_NAME","Leina Interview")
        self.maxq=int(os.getenv("INTERVIEW_MAX_QUESTIONS","20"))
        self.pass_score=int(os.getenv("INTERVIEW_PASS_SCORE","120"))
        self._task=None

    async def _ensure_thread(self):
        try:
            ch=self.bot.get_channel(self.learn) or await self.bot.fetch_channel(self.learn)
            thread=None
            if ch and getattr(ch,"threads",None):
                for t in ch.threads:
                    if getattr(t,"name","")==self.tname: thread=t; break
            if not thread and hasattr(ch,"create_thread"): thread=await ch.create_thread(name=self.tname)
            if thread: await self.us.set("interview:thread_id", str(thread.id)); return thread
        except Exception as e: log.warning("[interview] ensure_thread: %r", e)
        return None

    async def _post(self, dest, content): 
        try: await dest.send(content)
        except Exception as e: log.warning("[interview] post fail: %r", e)

    async def _next_q(self, thread, idx):
        if idx>=self.maxq: return None
        await self.us.set("interview:q_index", str(idx))
        await self._post(thread, f"**Q{idx+1}** — {QUESTIONS[idx % len(QUESTIONS)]}\n> Jawab: `Ya` / `Tidak` / `Tidak tahu`.")

    async def _start_if_needed(self, thread):
        st=await self.us.get("interview:status") or ""
        if st=="started": return
        await self.us.set("interview:status","started"); await self.us.set("interview:score","0"); await self.us.set("interview:q_index","0")
        mention=f"<@{self.owner}>" if self.owner else "@owner"
        await self._post(thread, f"Halo {mention}, aku mulai interview ya.")
        await self._next_q(thread,0)

    @commands.Cog.listener()
    async def on_ready(self):
        if self._task: return
        async def job():
            tid=await self.us.get("interview:thread_id"); thread=None
            if tid:
                try: thread=await self.bot.fetch_channel(int(tid))
                except Exception: thread=None
            if thread is None: thread=await self._ensure_thread()
            if thread is not None: await self._start_if_needed(thread)
        import asyncio; self._task=asyncio.create_task(job())

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            tid=await self.us.get("interview:thread_id")
            if not tid or str(getattr(message.channel,"id",""))!=str(tid): return
            if self.owner and int(getattr(message.author,"id",0))!=self.owner: return
            if getattr(message.author,"bot",False): return
            txt=(message.content or "").strip().lower()
            inc=10 if YES.search(txt) else (5 if UNK.search(txt) else (0 if NO.search(txt) else None))
            if inc is None: return
            score=await self.us.geti("interview:score",0)+inc; await self.us.set("interview:score",str(score))
            idx=await self.us.geti("interview:q_index",0)+1
            if score>=self.pass_score or idx>=self.maxq:
                await self.us.set("governor:interview_passed","1" if score>=self.pass_score else "0")
                await self.us.set("interview:status","finished")
                await self._post(message.channel, f"🏁 Selesai. Skor **{score}**/{self.maxq*10}. " + ("✅ *LULUS*. Gunakan `!gate unlock`." if score>=self.pass_score else "⭕ *Belum lulus*. `!interview reset`."))
            else:
                await self._next_q(message.channel, idx)
        except Exception as e: log.warning("[interview] on_message err: %r", e)

    @commands.group(name="interview", invoke_without_command=True)
    async def g_status(self, ctx):
        score=await self.us.geti("interview:score",0); st=await self.us.get("interview:status") or "idle"; q=await self.us.geti("interview:q_index",0)
        await ctx.reply(f"📋 status={st} | skor={score} | q={q}/{self.maxq} | pass≥{self.pass_score}", mention_author=False)

    @g_status.command(name="start")
    async def g_start(self, ctx):
        thread=None; tid=await self.us.get("interview:thread_id")
        try: thread=await self.bot.fetch_channel(int(tid)) if tid else None
        except Exception: thread=None
        if thread is None: thread=await self._ensure_thread()
        if thread is None: return await ctx.reply("❌ Tidak bisa membuat/menemukan thread.", mention_author=False)
        await self._start_if_needed(thread); await ctx.reply("▶️ Interview dimulai di thread.", mention_author=False)

    @g_status.command(name="reset")
    async def g_reset(self, ctx):
        for k,v in [("interview:status","idle"),("interview:score","0"),("interview:q_index","0"),("governor:interview_passed","0")]:
            await self.us.set(k,v)
        await ctx.reply("🔄 Interview di-reset.", mention_author=False)
async def setup(bot):
    await bot.add_cog(InterviewOverlay(bot))
def setup(bot):
    try:
        import asyncio; loop=None
        try: loop=asyncio.get_event_loop()
        except RuntimeError: pass
        return loop.create_task(setup(bot)) if (loop and loop.is_running()) else asyncio.run(setup(bot))
    except Exception: return None