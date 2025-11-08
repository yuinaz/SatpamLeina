from __future__ import annotations
import os, logging, asyncio
from typing import Optional, Tuple
log = logging.getLogger(__name__)
_TRUE = {"1","true","yes","on","y","t"}
def _flag(n, d=False): 
    v=os.getenv(n); 
    return d if v is None else (str(v).strip().lower() in _TRUE)
def _first(*keys, default=""):
    for k in keys:
        v = os.getenv(k, "")
        if v and str(v).strip():
            return str(v).strip()
    return default
def _split_order(v:str): 
    return [p.strip().lower() for p in (v or "").replace(";",",").split(",") if p.strip()] or ["gemini","groq"]
class QnaDualProvider:
    def __init__(self, bot=None):
        self.bot=bot
        self.order=_split_order(_first("QNA_PROVIDER_ORDER","QNA_PROVIDER_PRIORITY","QNA_PROVIDER","LEINA_AI_PROVIDER_ORDER","LLM_PROVIDER_ORDER","LLM_PROVIDER"))
        self.groq_model=os.getenv("GROQ_MODEL","llama-3.1-8b-instant")
        self.gemini_model=os.getenv("GEMINI_MODEL","gemini-2.5-flash-lite")
    async def aask(self, question:str) -> Tuple[Optional[str], Optional[str]]:
        forced=(os.getenv("QNA_FORCE_PROVIDER","") or "").strip().lower()
        strict=_flag("QNA_STRICT_FORCE", False)
        dis_gem=_flag("GEMINI_FORCE_DISABLE", False)
        dis_grq=_flag("GROQ_FORCE_DISABLE", False)
        async def _try(name:str):
            if name=="groq":
                t = await asyncio.to_thread(self._ask_groq, question)
                return t, ("Groq" if t else None)
            if name=="gemini":
                t = await asyncio.to_thread(self._ask_gemini, question)
                return t, ("Gemini" if t else None)
            return None, None
        if forced in ("groq","gemini"):
            if (forced=="groq" and not dis_grq) or (forced=="gemini" and not dis_gem):
                t, prov = await _try(forced)
                if t: return t, prov
                if strict: return None, None
        for name in self.order:
            if name=="groq" and dis_grq: continue
            if name=="gemini" and dis_gem: continue
            if forced and name==forced: 
                continue
            try:
                t, prov = await _try(name)
                if t: return t, prov
            except Exception as e:
                log.warning("[QnaDualProvider] %s failed: %r", name, e)
        return None, None
    def _ask_groq(self, prompt:str):
        key=os.getenv("GROQ_API_KEY") or ""
        if not key: return None
        try:
            from groq import Groq
            c=Groq(api_key=key)
            r=c.chat.completions.create(model=self.groq_model, messages=[{"role":"user","content":prompt}], temperature=0.2)
            return (r.choices[0].message.content or "").strip() or None
        except Exception as e:
            log.debug("[groq] error: %r", e); return None
    def _ask_gemini(self, prompt:str):
        key=os.getenv("GEMINI_API_KEY") or ""
        if not key: return None
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            m=genai.GenerativeModel(self.gemini_model)
            resp=m.generate_content(prompt)
            text=getattr(resp,"text",None)
            if not text and getattr(resp,"candidates",None):
                for cand in resp.candidates:
                    parts = getattr(getattr(cand,"content",None), "parts", None)
                    if parts:
                        text = "".join(getattr(p,"text","") for p in parts if hasattr(p,"text"))
                        if text: break
            return (text or "").strip() or None
        except Exception as e:
            log.debug("[gemini] error: %r", e); return None
