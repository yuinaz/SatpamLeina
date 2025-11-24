from __future__ import annotations

# satpambot/ai/groq_client.py
# -*- coding: utf-8 -*-
"""
Groq client helper — code-embedded controls (tidak perlu ENV Render):
- MODEL dipilih via konstanta di bawah
- Logging pemanggil LLM selalu aktif (bisa dimatikan di konstanta)
- Throttle global antar-call diatur via konstanta
- API key diambil dari secrets/local (get_secret), bukan ENV

Kalau mau ubah perilaku, edit konstanta di bawah lalu restart bot.
"""
import time, inspect, threading
from typing import List, Dict, Optional, Any

# ==== KONSTANTA (edit di sini jika perlu) ====
MODEL: str = "llama-3.1-8b-instant"   # Model Groq default
LOG_LLM_CALLS: bool = True            # Log pemanggil LLM
LLM_MIN_INTERVAL_S: float = 2.0       # Throttle global (detik). Set 0 untuk nonaktif.
# ============================================

try:
    from groq import Groq  # type: ignore
except Exception:  # pragma: no cover
    Groq = None  # biarkan import sukses saat SDK belum terpasang (smoke-safe)

# Ambil API key dari secrets/local (bukan ENV)
try:
    from satpambot.config.runtime import get_secret  # type: ignore
except Exception:
    def get_secret(name: str) -> Optional[str]:  # fallback super minimal
        return None

_lock = threading.RLock()
_last_call_ts = 0.0

def _maybe_wait():
    """Throttle global supaya tidak spam ke API."""
    global _last_call_ts
    gap = float(LLM_MIN_INTERVAL_S or 0.0)
    if gap <= 0:
        return
    with _lock:
        now = time.time()
        wait = _last_call_ts + gap - now
        if wait > 0:
            threading.Event().wait(wait if wait < gap else gap)
            now = time.time()
        _last_call_ts = now

def _log_call(messages: List[Dict]):
    if not LOG_LLM_CALLS:
        return
    # Coba identifikasi modul/fungsi pemanggil di dalam package
    mod = func = "?"
    try:
        for frame in inspect.stack()[1:]:
            fname = (frame.filename or "").replace("\\\\","/")
            if "/satpambot/" in fname and not fname.endswith("/ai/groq_client.py"):
                mod = fname.split("/satpambot/")[-1]
                func = frame.function
                break
        content_len = sum(len(m.get("content","") or "") for m in messages if m.get("role") in ("user","system"))
    except Exception:
        content_len = 0
    print(f"[LLM] caller={mod}:{func} content_len={content_len} model={MODEL}", flush=True)

class GroqLLM:
    def __init__(self, client: Any, model: Optional[str] = None, max_tokens: int = 256, timeout_s: int = 60):
        if client is None:
            raise RuntimeError("Groq client unavailable; install groq SDK or set secret GROQ_API_KEY.")
        self.client = client
        self.model = model or MODEL
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s

    def complete(self, messages: List[Dict]) -> str:
        _maybe_wait()
        _log_call(messages)
        p = {"max_tokens": self.max_tokens}
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, **p
        )
        return resp.choices[0].message.content

    def stream(self, messages: List[Dict]):
        _maybe_wait()
        _log_call(messages)
        p = {"max_tokens": self.max_tokens}
        stream = self.client.chat.completions.create(
            model=self.model, messages=messages, stream=True, **p
        )
        for chunk in stream:
            delta = getattr(chunk.choices[0], "delta", None)
            if delta and getattr(delta, "content", None):
                yield delta.content

def make_groq_client() -> Any:
    """Buat client Groq. API key diambil dari secrets/local (get_secret)."""
    if Groq is None:
        raise RuntimeError("Package 'groq' tidak tersedia. `pip install groq`.")
    api_key = (get_secret("GROQ_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY tidak ditemukan di secrets/local. "
                           "Taruh di: secrets/groq_api_key.txt atau di satpambot_config.local.json.secrets")
    return Groq(api_key=api_key)
