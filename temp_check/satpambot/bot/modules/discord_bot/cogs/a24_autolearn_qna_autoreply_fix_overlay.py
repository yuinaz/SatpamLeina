# -*- coding: utf-8 -*-
from discord.ext import commands
import os, time, hashlib, logging, asyncio

log=logging.getLogger(__name__)
def _norm(s): return " ".join((s or "").strip().split()).lower()
def _h(s): return hashlib.sha256((s or "").encode("utf-8")).hexdigest()

class Dedup(commands.Cog):
    def __init__(self,bot): self.bot=bot; self.ttl=int(os.getenv("QNA_DEDUP_WINDOW_SEC","90")); self._mem={}
    @commands.Cog.listener()
    async def on_message(self,m):
        try:
            if not getattr(m.author,"bot",False): return
            if not m.embeds: return
            e=m.embeds[0]; title=(getattr(e,"title","") or "").strip().lower()
            if title!="question by leina": return
            desc=(getattr(e,"description","") or "").strip()
            if not desc and getattr(e,"fields",None):
                for f in e.fields:
                    if getattr(f,"value",None): desc=f.value; break
            q=_norm(desc); 
            if not q: return
            key=str(getattr(getattr(m,"channel",None),"id",0)); h=_h(q)
            now=time.time(); prev=self._mem.get(key)
            if prev and prev[0]==h and (now-prev[1])<self.ttl:
                try: await m.delete(); log.info("[qna-dedup] delete dup in %s", key)
                except Exception: pass
            else:
                self._mem[key]=(h,now)
        except Exception as e:
            log.warning("[qna-dedup] on_message err: %r", e)

async def setup_async(bot): await bot.add_cog(Dedup(bot))

def setup(bot):
    try:
        loop = asyncio.get_event_loop()
        if loop and loop.is_running():
            return loop.create_task(setup_async(bot))
    except Exception:
        pass
    return asyncio.run(setup_async(bot))