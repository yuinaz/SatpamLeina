
import os, json, httpx, asyncio
from typing import List, Dict, Any, Optional

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_ROOT = "https://generativelanguage.googleapis.com/v1beta"



def _get_groq_model():
    return os.getenv("LLM_GROQ_MODEL") or "llama-3.1-8b-instant"


def _get_gemini_model():
    return os.getenv("LLM_GEMINI_MODEL") or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash-lite"


def _normalize_messages_for_openai(messages: List[Dict[str, str]], system: Optional[str]) -> List[Dict[str, str]]:
    mm = []
    if system:
        mm.append({"role": "system", "content": system})
    for m in messages:
        role = m.get("role") or "user"
        content = m.get("content") or ""
        mm.append({"role": role, "content": content})
    return mm

def _normalize_messages_for_gemini(messages: List[Dict[str, str]], system: Optional[str]) -> Dict[str, Any]:
    buf = []
    if system:
        buf.append(f"[system]: {system}")
    for m in messages:
        r = (m.get("role") or "user")
        c = (m.get("content") or "")
        if r == "assistant":
            r = "model"
        buf.append(f"[{r}]: {c}")
    text = "\n".join(buf) if buf else "Hello"
    return {"contents": [ { "role": "user", "parts": [ { "text": text } ] } ]}

async def ask(provider: str, model: str, messages: List[Dict[str, str]], system: Optional[str]=None,
              temperature: float=0.6, max_tokens: int=512, timeout: float=30.0, **kwargs) -> str:
    provider = (provider or "").lower()
    if provider in ("groq", "g", "openai"):
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY missing")
        payload = {
            "model": model,
            "messages": _normalize_messages_for_openai(messages, system),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=timeout) as cli:
            r = await cli.post(GROQ_URL, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        return data["choices"][0]["message"]["content"]
    else:
        if not GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY missing")
        model_path = f"models/{model}"
        url = f"{GEMINI_ROOT}/{model_path}:generateContent?key={GOOGLE_API_KEY}"
        payload = _normalize_messages_for_gemini(messages, system)
        headers = {"Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=timeout) as cli:
            r = await cli.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return json.dumps(data)[:800]

def ask_sync(*args, **kwargs) -> str:
    return asyncio.get_event_loop().run_until_complete(ask(*args, **kwargs))
