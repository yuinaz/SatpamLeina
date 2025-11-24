
import json, os, pathlib
from typing import Any, Optional, Dict

_CACHE: Dict[str, Any] = {}
_LOADED = False
_CANDIDATES = [
    "local.json",
    "config/local.json",
    "satpambot_config.local.json",
    "config/satpambot_config.local.json",
    "data/config/satpambot_config.local.json",
    "satpambot.local.json",
]

def _safe_json_load(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _load_if_needed():
    global _LOADED, _CACHE
    if _LOADED: return
    for cand in _CANDIDATES:
        p = pathlib.Path(cand)
        if p.exists():
            data = _safe_json_load(str(p))
            if isinstance(data, dict):
                _CACHE = data
                _LOADED = True
                return
    _CACHE = {}
    _LOADED = True

def _from_env(key: str) -> Optional[str]:
    return os.environ.get(key)

def _coerce(value: Any, cast: Any):
    if cast is None:
        return value
    try:
        if cast is bool:
            if isinstance(value, str):
                return value.strip().lower() in ("1","true","yes","on","y")
            return bool(value)
        if cast in (int, float):
            return cast(value)
        return cast(value)
    except Exception:
        return value

def get(key: str, default: Any=None, cast=None):
    _load_if_needed()
    cur = _CACHE
    found = None
    if "." in key:
        parts = key.split(".")
        for i, part in enumerate(parts):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
                if i == len(parts)-1:
                    found = cur
            else:
                found = None
                break
    else:
        found = _CACHE.get(key)
    if found is None:
        envv = _from_env(key)
        if envv is not None:
            return _coerce(envv, cast) if cast else envv
        return default
    return _coerce(found, cast) if cast else found
