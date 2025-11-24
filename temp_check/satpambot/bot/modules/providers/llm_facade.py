
import os, json, logging
from typing import List, Dict, Optional

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None

log = logging.getLogger(__name__)

GROQ_URL = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1/chat/completions")
GEM_URL_TMPL = os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent")

def _coerce_messages(system: str, messages: List[Dict]) -> str:
    sys = (system or "").strip()
    chunks = []
    if sys:
        chunks.append(f"[SYSTEM]\\n{sys}")
    for m in messages or []:
        role = m.get("role","user")
        content = (m.get("content") or "").strip()
        chunks.append(f"[{role.upper()}]\\n{content}")
    return "\\n\\n".join(chunks).strip()

def _build_timeout():
    """Build an httpx timeout that is compatible across httpx versions."""
    if httpx is None:
        return 15.0
    try:
        # Newer httpx supports per-phase keywords
        return httpx.Timeout(15.0, connect=8.0)
    except TypeError:
        # Older httpx only takes a single float
        try:
            return httpx.Timeout(15.0)
        except Exception:
            return 15.0

async def _ask_groq(model: Optional[str], system: str, messages: List[Dict], temperature: float, max_tokens: int) -> str:
    if httpx is None:
        raise RuntimeError("httpx not installed")
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY missing")
    mdl = model or os.getenv("GROQ_MODEL","llama-3.1-8b-instant")
    payload = {
        "model": mdl,
        "messages": [{"role":"system","content": system}] + [{"role":m.get("role","user"),"content":m.get("content","")} for m in messages],
        "temperature": float(temperature or 0.7),
        "max_tokens": int(max_tokens or 320),
        "stream": False
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type":"application/json"}
    timeout = _build_timeout()
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(GROQ_URL, headers=headers, json=payload)
        if r.status_code >= 300:
            raise RuntimeError(f"groq http {r.status_code}: {r.text[:200]}")
        data = r.json()
        try:
            return (data["choices"][0]["message"]["content"] or "").strip()
        except Exception:
            raise RuntimeError(f"groq bad response: {json.dumps(data)[:200]}")

async def _ask_gemini(model: Optional[str], system: str, messages: List[Dict], temperature: float, max_tokens: int) -> str:
    if httpx is None:
        raise RuntimeError("httpx not installed")
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing")
    mdl = model or os.getenv("GEMINI_MODEL","gemini-2.5-flash-lite")
    url = GEM_URL_TMPL.format(model=mdl)
    url = f"{url}?key={key}"
    text = _coerce_messages(system, messages)
    payload = {
        "contents": [ { "role": "user", "parts": [ { "text": text } ] } ],
        "generationConfig": {
            "temperature": float(temperature or 0.7),
            "maxOutputTokens": int(max_tokens or 320)
        }
    }
    timeout = _build_timeout()
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, json=payload)
        if r.status_code >= 300:
            raise RuntimeError(f"gemini http {r.status_code}: {r.text[:200]}")
        data = r.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
            buf = []
            for p in parts:
                if "text" in p:
                    buf.append(p["text"])
            return "\\n".join(buf).strip()
        except Exception:
            raise RuntimeError(f"gemini bad response: {json.dumps(data)[:200]}")

async def ask(provider: str, model: Optional[str], system: str, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 320) -> str:
    prov = (provider or "").strip().lower()
    if prov == "groq":
        return await _ask_groq(model, system, messages, temperature, max_tokens)
    if prov == "gemini":
        return await _ask_gemini(model, system, messages, temperature, max_tokens)
    raise ValueError(f"unknown provider: {provider}")
