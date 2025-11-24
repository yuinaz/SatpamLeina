# -*- coding: utf-8 -*-
"""
a24_qna_dedup_guard_overlay
- Dedup "Question by Leina" per channel (TTL=90s)
- Hash isi pertanyaan + title; hapus duplikat cepat
- Aman untuk Render Free (no network)
Env: QNA_DEDUP_WINDOW_SEC=90
"""
from discord.ext import commands
import os, time, hashlib, logging

log=logging.getLogger(__name__)

def _norm(s): return " ".join((s or "").strip().split()).lower()
def _h(s): return hashlib.sha256((s or "").encode("utf-8")).hexdigest()

class QnaDedup(commands.Cog):
    def __init__(self,bot):
        self.bot=bot
        self.ttl=int(os.getenv("QNA_DEDUP_WINDOW_SEC","90") or "90")
        self.cache={}  # channel_id -> (hash, ts)

    @commands.Cog.listener()
    async def on_message(self,m):
        try:
            if not getattr(m.author,"bot",False): return
            if not m.embeds: return
            e=m.embeds[0]
            title=(getattr(e,"title","") or "").strip().lower()
            if title!="question by leina": return
            # ambil konten
            desc=(getattr(e,"description","") or "") or ""
            try:
                # cari content di fields jika kosong
                if not desc and getattr(e,"fields",None):
                    for f in e.fields:
                        if getattr(f,"value",None):
                            desc=f.value or ""; break
            except Exception: pass
            q=_norm(desc)
            if not q: return
            key=str(getattr(getattr(m,"channel",None),"id",0))
            now=time.time()
            h=_h(title+"|"+q)
            prev=self.cache.get(key)
            if prev and prev[0]==h and (now-prev[1])<self.ttl:
                try:
                    await m.delete()
                    log.info("[qna-dedup] dup removed in %s", key)
                except Exception as e:
                    log.debug("[qna-dedup] delete fail: %r", e)
            else:
                self.cache[key]=(h,now)
        except Exception as e:
            log.warning("[qna-dedup] err: %r", e)
async def setup(bot): await bot.add_cog(QnaDedup(bot))