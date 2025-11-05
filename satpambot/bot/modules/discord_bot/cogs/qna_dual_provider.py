from __future__ import annotations
import os, logging, asyncio
from typing import Optional, Tuple
log = logging.getLogger(__name__)
def _split_order(v: str) -> list[str]:
    parts = []
    for p in (v or "").replace(";", ",").split(","):
        p = p.strip().lower()
        if p: parts.append(p)
    return parts or ["groq","gemini"]
class QnaDualProvider:
    def __init__(self, bot=None):
        self.bot = bot
        self.order = _split_order(os.getenv("QNA_PROVIDER_ORDER", "groq,gemini"))
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    async def aask(self, question: str) -> Tuple[Optional[str], Optional[str]]:
        for name in self.order:
            try:
                if name == "groq":
                    text = await asyncio.to_thread(self._ask_groq, question)
                    if text: return text, "Groq"
                if name == "gemini":
                    text = await asyncio.to_thread(self._ask_gemini, question)
                    if text: return text, "Gemini"
            except Exception as e:
                log.warning("[QnaDualProvider] %s failed: %r", name, e)
                continue
        return None, None
    def _ask_groq(self, prompt: str) -> Optional[str]:
        key = os.getenv("GROQ_API_KEY") or ""
        if not key: return None
        try:
            from groq import Groq  # type: ignore
            client = Groq(api_key=key)
            res = client.chat.completions.create(
                model=self.groq_model,
                messages=[{"role":"user","content":prompt}], temperature=0.2
            )
            return (res.choices[0].message.content or "").strip() or None
        except Exception as e:
            log.debug("[QnaDualProvider] groq error: %r", e); return None
    def _ask_gemini(self, prompt: str) -> Optional[str]:
        key = os.getenv("GEMINI_API_KEY") or ""
        if not key: return None
        try:
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=key)
            model = genai.GenerativeModel(self.gemini_model)
            resp = model.generate_content(prompt)
            text = getattr(resp, "text", None)
            if not text and getattr(resp, "candidates", None):
                for cand in resp.candidates:
                    parts = getattr(getattr(cand, "content", None), "parts", None)
                    if parts:
                        text = "".join(getattr(p,"text","") for p in parts if hasattr(p,"text"))
                        if text: break
            return (text or "").strip() or None
        except Exception as e:
            log.debug("[QnaDualProvider] gemini error: %r", e); return None
