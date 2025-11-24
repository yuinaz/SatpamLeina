from __future__ import annotations
import os, json, threading
from pathlib import Path
from typing import Any, Optional

_CFG_CACHE: dict[str, Any] = {}
_CFG_LOCK = threading.Lock()
_CFG_FILES = [
    Path("data/config/runtime_env.json"),
    Path("data/config/overrides.render-free.json"),
    Path("data/config/overrides_render.json"),
    Path("data/config/passive_bridge.json"),
]

def _load_json() -> dict[str, Any]:
    with _CFG_LOCK:
        if _CFG_CACHE: return _CFG_CACHE
        merged: dict[str, Any] = {}
        for p in _CFG_FILES:
            try:
                if p.exists():
                    raw = p.read_text(encoding="utf-8")
                    if not raw.strip(): 
                        continue
                    d = json.loads(raw)
                    if isinstance(d, dict):
                        if "env" in d and isinstance(d["env"], dict):
                            merged.update(d["env"])
                        # top-level keys also allowed
                        for k,v in d.items():
                            if k != "env":
                                merged[k] = v
            except Exception:
                # ignore malformed files
                pass
        _CFG_CACHE.update(merged)
        return _CFG_CACHE

def cfg_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """ENV-first for secrets (tokens, api keys, urls)."""
    v = os.getenv(key, None)
    if v not in (None, ""):
        return v
    # fallback to json files
    merged = _load_json()
    if key in merged and isinstance(merged[key], str) and merged[key] != "":
        return merged[key]
    # last resort: auto_defaults if available
    try:
        from satpambot.config.auto_defaults import cfg_str as real  # type: ignore
        x = real(key, default)
        if x not in (None, ""):
            return x
    except Exception:
        pass
    return default

def cfg_str(key: str, default: Optional[str] = None) -> Optional[str]:
    """JSON-first for regular config; fallback ENV, then auto_defaults."""
    merged = _load_json()
    if key in merged and isinstance(merged[key], str) and merged[key] != "":
        return merged[key]
    v = os.getenv(key, None)
    if v not in (None, ""):
        return v
    try:
        from satpambot.config.auto_defaults import cfg_str as real  # type: ignore
        x = real(key, default)
        if x not in (None, ""):
            return x
    except Exception:
        pass
    return default

def cfg_int(key: str, default: int) -> int:
    v = cfg_str(key, None)
    try: return int(v) if v is not None else int(default)
    except Exception: return int(default)

def cfg_float(key: str, default: float) -> float:
    v = cfg_str(key, None)
    try: return float(v) if v is not None else float(default)
    except Exception: return float(default)