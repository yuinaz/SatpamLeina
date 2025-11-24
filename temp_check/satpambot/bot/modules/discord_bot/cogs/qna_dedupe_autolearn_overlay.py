\
from __future__ import annotations
import os, re, logging, time
from typing import Optional
try:
    import discord
    from discord.ext import commands
except Exception:
    class discord:  # type: ignore
        class Message: ...
        class Embed:
            def __init__(self,*a,**k): ...
            title=''; description=''; author=type('A',(),{'name':''})()
            footer=type('F',(),{'text':''})()
    class commands:  # type: ignore
        class Cog:
            @staticmethod
            def listener(*a,**k):
                def _w(f): return f
                return _w
        @staticmethod
        def listener(*a,**k):
            def _w(f): return f
            return _w
from satpambot.config.auto_defaults import cfg_int, cfg_str
log=logging.getLogger(__name__)
QID=cfg_int("QNA_CHANNEL_ID",None)
WINDOW_SEC=int(cfg_str("QNA_DEDUPE_WINDOW_SEC","900") or "900")
HIST_LIMIT=int(cfg_str("QNA_DEDUPE_HISTORY","30") or "30")
DELETE_NON_EMBED=(cfg_str("QNA_DELETE_NON_EMBED","1") or "1").lower() in ("1","true","yes","on")
_RX_Q=re.compile(r'\b(question|pertanyaan)\b',re.I)
_RX_A=re.compile(r'\banswer\s+by\s+(groq|gemini)\b',re.I)
def _txt(e:'discord.Embed')->str:
    g=lambda x:(x or '').strip().lower()
    return ' '.join([g(getattr(e,'title','')), g(getattr(getattr(e,'author',None),'name',None)), g(getattr(e,'description','')), g(getattr(getattr(e,'footer',None),'text',None))])
def _is_q(e): t=_txt(e); return (_RX_A.search(t) is None) and (_RX_Q.search(t) is not None)
def _is_a(e):
    t=_txt(e); m=_RX_A.search(t)
    if m: return m.group(1).lower()
    if "qna_provider:" in t:
        if "groq" in t: return "groq"
        if "gemini" in t: return "gemini"
    return None
async def _del(m:'discord.Message'):
    try: await m.delete(); return True
    except Exception as e: log.debug('[qna-dedupe] delete fail: %r',e); return False
class QnaDedupeAutolearn(commands.Cog):
    def __init__(self,bot): self.bot=bot; self.qid=QID; log.info('[qna-dedupe] ready ch=%s',self.qid)
    @commands.Cog.listener()
    async def on_message(self,m:'discord.Message'):
        try:
            if not self.qid: return
            if getattr(getattr(m,'channel',None),'id',None)!=self.qid: return
            if DELETE_NON_EMBED and (not getattr(m,'embeds',None) or len(m.embeds)==0):
                await _del(m); return
            if not getattr(m,'embeds',None) or len(m.embeds)==0: return
            if not getattr(getattr(m,'author',None),'bot',False): return
            e_new=m.embeds[0]
            hist=getattr(m.channel,'history',None)
            if not callable(hist): return
            now=time.time()
            async for old in m.channel.history(limit=HIST_LIMIT, oldest_first=False):
                if old.id==m.id: continue
                if not getattr(old,'embeds',None) or len(old.embeds)==0: continue
                if not getattr(getattr(old,'author',None),'bot',False): continue
                e_old=old.embeds[0]
                ts=getattr(old,'created_at',None)
                age= now-(ts.timestamp() if hasattr(ts,'timestamp') else 0)
                if age>WINDOW_SEC: break
                if _is_q(e_new) and _is_q(e_old):
                    if (getattr(e_new,'description','').strip().lower()==getattr(e_old,'description','').strip().lower()):
                        await _del(m); return
                p_new=_is_a(e_new); p_old=_is_a(e_old)
                if p_new and p_old and p_new==p_old:
                    await _del(m); return
        except Exception as ex:
            log.warning('[qna-dedupe] fail: %r',ex)
async def setup(bot):
    await bot.add_cog(QnaDedupeAutolearn(bot))
