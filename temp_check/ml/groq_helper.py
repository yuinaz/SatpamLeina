
import os, time
from typing import Optional, List
from satpambot.config.compat_conf import get as cfg

GROQ_API_KEY = cfg("GROQ_API_KEY", None, str) or os.environ.get("GROQ_API_KEY")
GROQ_BASE_URL = cfg("GROQ_BASE_URL", "https://api.groq.com/openai/v1", str)
GROQ_MODEL = cfg("GROQ_MODEL", "llama-3.1-8b-instant", str)

_client = None
_disabled_until = 0.0

def _get_client():
    global _client
    if _client is not None:
        return _client
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL) if GROQ_API_KEY else None
    except Exception:
        _client = None
    return _client

def ask_system(question: str, examples: Optional[List[str]] = None) -> Optional[str]:
    global _disabled_until
    if time.time() < _disabled_until:
        return None
    client = _get_client()
    if not client:
        return None
    messages = [{"role":"system","content":"You are a concise assistant for Discord moderation tooling. Keep answers short and actionable."}]
    if examples:
        messages.append({"role":"user","content":"\n".join(examples)})
        messages.append({"role":"assistant","content":"Noted examples."})
    messages.append({"role":"user","content":question})
    try:
        resp = client.chat.completions.create(model=GROQ_MODEL, messages=messages, temperature=0.2, max_tokens=300)
        return resp.choices[0].message.content
    except Exception as e:
        if "403" in str(e) or "Forbidden" in str(e):
            _disabled_until = time.time() + 3600
        return None
