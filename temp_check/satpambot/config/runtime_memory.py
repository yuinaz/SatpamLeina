from __future__ import annotations

import json, os, pathlib, threading
from typing import Any, Dict, Optional
from .compat_conf import get as file_first_get

_LOCK = threading.RLock()
_MEM: Dict[str, Any] = {}
_CONFIG_FILE: Optional[str] = None

def _init_config_file() -> str:
    global _CONFIG_FILE
    if _CONFIG_FILE:
        return _CONFIG_FILE
    for cand in [
        "satpambot_config.local.json",
        "config/satpambot_config.local.json",
        "data/config/satpambot_config.local.json",
        "satpambot.local.json",
    ]:
        if pathlib.Path(cand).exists():
            _CONFIG_FILE = cand
            break
    if not _CONFIG_FILE:
        _CONFIG_FILE = "satpambot_config.local.json"
    return _CONFIG_FILE

def load_from_disk() -> None:
    path = _init_config_file()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    with _LOCK:
        _MEM.clear()
        _MEM.update(data)

def save_to_disk() -> None:
    path = _init_config_file()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_MEM, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def get(key: str, default: Any=None) -> Any:
    with _LOCK:
        if key in _MEM:
            return _MEM[key]
    return file_first_get(key, default)

def set(key: str, value: Any, persist: bool=False) -> None:
    with _LOCK:
        _MEM[key] = value
    if persist:
        save_to_disk()

def all() -> Dict[str, Any]:
    with _LOCK:
        return dict(_MEM)

try:
    load_from_disk()
except Exception:
    pass
