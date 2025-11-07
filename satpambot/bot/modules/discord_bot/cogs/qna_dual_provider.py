from __future__ import annotations
import os, logging, asyncio
from typing import Optional, Tuple

log = logging.getLogger(__name__)

_TRUE = {"1","true","yes","on","y","t"}

def _flag(name: str, default: bool=False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in _TRUE

def _split_order(v: str) -> list[str]:
    parts = []
    for p in (v or "").replace(";", ",").split(","):
        p = p.strip().lower()
        if p:
            parts.append(p)
    return parts or ["groq", "gemini"]

def _resolve_order() -> list[str]:
    # support multiple synonyms; first non-empty wins
    for key in ("QNA_PROVIDER_ORDER","QNA_PROVIDER_PRIORITY","QNA_PROVIDER",
                "LEINA_AI_PROVIDER_ORDER","LLM_PROVIDER_ORDER","LLM_PROVIDER"):
        val = os.getenv(key)
        if val and str(val).strip():
            return _split_order(str(val))
    return ["groq","gemini"]

class QnaDualProvider:
    def __init__(self, bot=None):
        self.bot = bot
        self.order = _resolve_order()
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

    async def aask(self, question: str) -> Tuple[Optional[str], Optional[str]]:
        forced = (os.getenv("QNA_FORCE_PROVIDER","") or "").strip().lower()
        strict = _flag("QNA_STRICT_FORCE", False)
        disable_gem = _flag("GEMINI_FORCE_DISABLE", False)
        disable_groq = _flag("GROQ_FORCE_DISABLE", False)

        async def _try(name: str) -> Tuple[Optional[str], Optional[str]]:
            if name == "groq":
                text = await asyncio.to_thread(self._ask_groq, question)
                if text: return text, "Groq"
                return None, None
            if name == "gemini":
                text = await asyncio.to_thread(self._ask_gemini, question)
                if text: return text, "Gemini"
                return None, None
            return None, None

        # 1) Strict forced mode: only use the forced provider
        if forced in ("groq","gemini"):
            if (forced == "groq" and disable_groq) or (forced == "gemini" and disable_gem):
                # forced but disabled; in strict mode -> refuse
                if strict:
                    return None, None
            text, prov = await _try(forced)
            if text:
                return text, prov
            # If strict, never fallback
            if strict:
                return None, None
            # else: fall through to normal order below

        # 2) Normal ordered attempts, skipping disabled providers
        for name in self.order:
            if name == "groq" and disable_groq: 
                continue
            if name == "gemini" and disable_gem: 
                continue
            # avoid repeating the provider we already tried above
            if forced and name == forced:
                # already attempted in non-strict case
                continue
            try:
                text, prov = await _try(name)
                if text:
                    return text, prov
            except Exception as e:
                log.warning("[QnaDualProvider] %s failed: %r", name, e)
                continue
        return None, None

    def _ask_groq(self, prompt: str) -> Optional[str]:
        key = os.getenv("GROQ_API_KEY") or ""
        if not key:
            return None
        try:
            from groq import Groq  # type: ignore
            client = Groq(api_key=key)
            res = client.chat.completions.create(
                model=self.groq_model,
                messages=[{"role":"user","content":prompt}],
                temperature=0.2,
            )
            return (res.choices[0].message.content or "").strip() or None
        except Exception as e:
            log.debug("[QnaDualProvider] groq error: %r", e)
            return None

    def _ask_gemini(self, prompt: str) -> Optional[str]:
        key = os.getenv("GEMINI_API_KEY") or ""
        if not key:
            return None
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
                        if text:
                            break
            return (text or "").strip() or None
        except Exception as e:
            log.debug("[QnaDualProvider] gemini error: %r", e)
            return None