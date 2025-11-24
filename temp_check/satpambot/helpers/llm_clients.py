import os, asyncio, aiohttp
from typing import Optional

def _norm_base_groq() -> str:
    base = os.getenv("OPENAI_BASE_URL") or os.getenv("GROQ_BASE_URL") or "https://api.groq.com"
    base = base.rstrip("/")
    return base if base.endswith("/openai/v1") else base + "/openai/v1"

def _get(key: str, default: str = "") -> str:
    v = os.getenv(key, "")
    return v if v else default


def _get_gemini_model():
    return os.getenv("LLM_GEMINI_MODEL") or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash-lite"



def _get_groq_model():
    return os.getenv("LLM_GROQ_MODEL") or "llama-3.1-8b-instant"


class GeminiClient:
    def __init__(self, api_key: Optional[str]=None, model: Optional[str]=None, api_base: Optional[str]=None):
        self.key = api_key or _get("GEMINI_API_KEY")
        self.model = model or _get("LLM_GEMINI_MODEL", _get("GEMINI_MODEL", "gemini-1.5-flash"))
        self.base = (api_base or _get("GEMINI_API_BASE", "https://generativelanguage.googleapis.com")).rstrip("/")
        self.timeout = float(_get("GEMINI_HTTP_TIMEOUT_SEC", "30"))
        self.max_retries = int(_get("GEMINI_HTTP_RETRIES", "2"))
        self.retry_backoff = float(_get("GEMINI_HTTP_BACKOFF_SEC", "1.0"))
    def available(self) -> bool:
        return bool(self.key)
    async def answer(self, prompt: str, system: str) -> str:
        url = f"{self.base}/v1beta/models/{self.model}:generateContent?key={self.key}"
        payload = {"contents": [{"role":"user","parts":[{"text": prompt}]}],
                   "generationConfig": {"temperature": 0.4, "maxOutputTokens": 400}}
        if system:
            payload["systemInstruction"] = {"role": "system", "parts": [{"text": system}]}
        last_err = None
        for attempt in range(self.max_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as sess:
                    async with sess.post(url, json=payload) as r:
                        if r.status >= 500 or r.status == 429:
                            last_err = RuntimeError(f"Gemini {r.status}: {await r.text()}")
                            if attempt < self.max_retries:
                                await asyncio.sleep(self.retry_backoff * (2 ** attempt)); continue
                        if r.status != 200:
                            raise RuntimeError(f"Gemini {r.status}: {await r.text()}")
                        j = await r.json()
                        try:
                            return (j["candidates"][0]["content"]["parts"][0]["text"] or "").strip()
                        except Exception:
                            parts = j.get("candidates",[{}])[0].get("content",{}).get("parts",[])
                            if parts and isinstance(parts,list):
                                if isinstance(parts[0],dict) and "text" in parts[0]: return (parts[0]["text"] or "").strip()
                            raise RuntimeError("Gemini returned unexpected schema")
            except Exception as e:
                last_err = e
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_backoff * (2 ** attempt)); continue
        raise last_err or RuntimeError("Gemini failed")

class GroqClient:
    def __init__(self, api_key: Optional[str]=None, model: Optional[str]=None):
        self.key = api_key or _get("GROQ_API_KEY")
        self.model = model or _get("LLM_GROQ_MODEL", _get("GROQ_MODEL", "llama-3.1-8b-instant"))
        self.base = _norm_base_groq().rstrip("/")
        self.timeout = float(_get("GROQ_HTTP_TIMEOUT_SEC","30"))
        self.max_retries = int(_get("GROQ_HTTP_RETRIES","2"))
        self.retry_backoff = float(_get("GROQ_HTTP_BACKOFF_SEC","1.0"))
        self.url = f"{self.base}/chat/completions"
    def available(self) -> bool:
        return bool(self.key)
    async def answer(self, prompt: str, system: str) -> str:
        headers = {"Authorization": f"Bearer {self.key}"}
        payload = {"model": self.model,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": prompt}],
                   "temperature": 0.4, "max_tokens": 400}
        last_err = None
        for attempt in range(self.max_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as sess:
                    async with sess.post(self.url, headers=headers, json=payload) as r:
                        if r.status >= 500 or r.status == 429:
                            last_err = RuntimeError(f"Groq {r.status}: {await r.text()}")
                            if attempt < self.max_retries:
                                await asyncio.sleep(self.retry_backoff * (2 ** attempt)); continue
                        if r.status != 200:
                            raise RuntimeError(f"Groq {r.status}: {await r.text()}")
                        j = await r.json()
                        try:
                            return (j["choices"][0]["message"]["content"] or "").strip()
                        except Exception:
                            raise RuntimeError("Groq returned unexpected schema")
            except Exception as e:
                last_err = e
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_backoff * (2 ** attempt)); continue
        raise last_err or RuntimeError("Groq failed")

class QnaClient:
    def __init__(self):
        self.gemini = GeminiClient()
        self.groq = GroqClient()
    async def answer(self, prompt: str, system: str) -> str:
        if self.gemini.available():
            try: return await self.gemini.answer(prompt, system)
            except Exception: pass
        if self.groq.available():
            try: return await self.groq.answer(prompt, system)
            except Exception: pass
        return "(fallback) Maaf, aku belum bisa menjawab sekarang."
