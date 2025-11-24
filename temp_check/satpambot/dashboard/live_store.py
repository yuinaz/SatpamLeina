from __future__ import annotations

"""
live_store.py
- Persistent pHash store for phishing images
- In-memory cache with safe file-backed JSON: data/phish/phash.json
- Optional bot notify hook if present
"""
import os, json, threading
from pathlib import Path

_lock = threading.RLock()
_cache = None
_store_path = Path("data/phish/phash.json")  # shared between web & bot

def _ensure_dir():
    _store_path.parent.mkdir(parents=True, exist_ok=True)

def _load() -> list[str]:
    global _cache
    with _lock:
        if _cache is not None:
            return list(_cache)
        try:
            if _store_path.exists():
                data = json.loads(_store_path.read_text("utf-8"))
                _cache = [str(x) for x in (data.get("phash") if isinstance(data, dict) else data) or []]
            else:
                _cache = []
        except Exception:
            _cache = []
        return list(_cache)

def _save(lst: list[str]) -> None:
    with _lock:
        _ensure_dir()
        try:
            _store_path.write_text(json.dumps({"phash": lst}, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

def get_phash() -> list[str]:
    return _load()

def add_phash(v: str) -> list[str]:
    v = str(v).strip()
    if not v:
        return get_phash()
    with _lock:
        cur = _load()
        if v not in cur:
            cur.append(v)
            _save(cur)
            _notify_bot_phash_updated(cur)
        return list(cur)

def _notify_bot_phash_updated(cur: list[str]) -> None:
    """Best-effort notify running bot process (optional)."""
    # Strategy: write to shared file (done), and attempt to call optional hook if loaded
    try:
        # If bot exposes a hook (you can implement this), call it
        from satpambot.bot.modules.discord_bot.web_api import on_phash_updated  # type: ignore
        try:
            on_phash_updated(cur)  # type: ignore
        except Exception:
            pass
    except Exception:
        pass
