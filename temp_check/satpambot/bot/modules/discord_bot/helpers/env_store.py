from __future__ import annotations

# satpambot.bot.modules.discord_bot.helpers.env_store
# Lightweight, file-based ENV key-value store.
# Drop-in module so imports like `from ..helpers import env_store` work.

import os
import json
import threading
from typing import Any, Dict, Iterable, Optional

_LOCK = threading.RLock()
# Where to keep the env store file:
# 1) SATPAMBOT_DATA_DIR (preferred) -> env/kv.json
# 2) ./data/env/kv.json relative to CWD
def _base_dir() -> str:
    base = os.getenv("SATPAMBOT_DATA_DIR")
    if base:
        return base
    # fallback to repo-local ./data
    return os.path.abspath(os.path.join(os.getcwd(), "data"))

def _env_dir() -> str:
    d = os.path.join(_base_dir(), "env")
    os.makedirs(d, exist_ok=True)
    return d

def db_path() -> str:
    return os.path.join(_env_dir(), "kv.json")

def _read() -> Dict[str, Any]:
    p = db_path()
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Corrupted or unreadable => start fresh (do not crash boot)
        return {}

def _write(data: Dict[str, Any]) -> None:
    p = db_path()
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, p)

# Public APIs (generic & friendly)
def load() -> Dict[str, Any]:
    with _LOCK:
        return dict(_read())

def save(data: Dict[str, Any]) -> None:
    with _LOCK:
        _write(dict(data))

def get(key: str, default: Any=None) -> Any:
    with _LOCK:
        return _read().get(key, default)

def set(key: str, value: Any) -> None:
    with _LOCK:
        d = _read()
        d[str(key)] = value
        _write(d)

def set_many(items: Dict[str, Any]) -> None:
    with _LOCK:
        d = _read()
        d.update({str(k): v for k, v in items.items()})
        _write(d)

def delete(key: str) -> None:
    with _LOCK:
        d = _read()
        if key in d:
            del d[key]
            _write(d)

def clear() -> None:
    with _LOCK:
        _write({})

# Helpers
def get_bool(key: str, default: bool=False) -> bool:
    v = get(key, None)
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    return s in ("1","true","yes","on","y")

def get_int(key: str, default: Optional[int]=None) -> Optional[int]:
    v = get(key, None)
    if v is None:
        return default
    try:
        return int(v)
    except Exception:
        return default

# Import/export from process env
def import_all(prefix: Optional[str]=None, allow: Optional[Iterable[str]]=None, deny: Optional[Iterable[str]]=None) -> int:
    allow = set(allow or [])
    deny = set(deny or [])
    count = 0
    with _LOCK:
        d = _read()
        for k, v in os.environ.items():
            if prefix and not k.startswith(prefix):
                continue
            if allow and k not in allow:
                continue
            if k in deny:
                continue
            d[k] = v
            count += 1
        _write(d)
    return count

def export_to_os(overwrite: bool=False) -> int:
    with _LOCK:
        d = _read()
    count = 0
    for k, v in d.items():
        if not overwrite and k in os.environ:
            continue
        os.environ[str(k)] = str(v)
        count += 1
    return count

# A couple of conventional convenience getters (optional use)
def owner_id() -> Optional[int]:
    oid = get("OWNER_USER_ID", None)
    try:
        return int(oid) if oid is not None else None
    except Exception:
        return None

def runtime_ready_delay() -> int:
    return get_int("READY_DELAY_SECS", 0)

