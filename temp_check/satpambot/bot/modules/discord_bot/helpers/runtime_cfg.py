from __future__ import annotations

import os, json, time, threading
from pathlib import Path
from typing import Any, Dict

CONFIG_PATH = Path(os.getenv("SATPAMBOT_RUNTIME_CFG", "data/runtime_config.json"))
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

DEFAULTS: Dict[str, Any] = {
    "status_pin": {
        "enabled": True,
        "interval_min": 5,
        "jitter_min_s": 10,
        "jitter_max_s": 20
    },
    "log": { "channel_id": None, "channel_name": None },
    "reaction_allow": { "extra_ids": [], "names": [] },
    "config_source": { "channel_id": None, "message_id": None }
}

def deep_get(d: Dict[str, Any], path: str, default: Any=None) -> Any:
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur

def deep_set(d: Dict[str, Any], path: str, value: Any) -> None:
    parts = path.split("."); cur = d
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict): cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value

class ConfigManager:
    _instance = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self.path = CONFIG_PATH
        self._data: Dict[str, Any] = {}
        self._mtime: float = 0.0
        self.reload()

    @classmethod
    def instance(cls) -> "ConfigManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = ConfigManager()
            return cls._instance

    def _merge_defaults(self, data):
        def merge(a, b):
            for k, v in b.items():
                if isinstance(v, dict): a[k] = merge(a.get(k, {}), v)
                elif k not in a: a[k] = v
            return a
        out = merge({}, DEFAULTS.copy())
        out = merge(out, data or {})
        log_id = os.getenv("LOG_CHANNEL_ID") or os.getenv("STATUS_CHANNEL_ID") or os.getenv("LOG_BOTPHISING_ID") or os.getenv("LOG_BOTPHISHING_ID")
        if log_id and str(log_id).isdigit(): out["log"]["channel_id"] = int(str(log_id))
        log_name = os.getenv("LOG_CHANNEL_NAME") or os.getenv("STATUS_CHANNEL_NAME")
        if log_name: out["log"]["channel_name"] = str(log_name)
        extra_ids = os.getenv("REACTION_ALLOW_CH_IDS")
        if extra_ids:
            xs = [int(t) for t in str(extra_ids).replace(" ", "").split(",") if t.isdigit()]
            out["reaction_allow"]["extra_ids"] = xs
        extra_names = os.getenv("REACTION_ALLOW_NAMES")
        if extra_names:
            out["reaction_allow"]["names"] = [t.strip() for t in str(extra_names).split(",") if t.strip()]
        return out

    def reload(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        except Exception:
            raw = {}
        self._data = self._merge_defaults(raw)
        try:
            self._mtime = self.path.stat().st_mtime
        except Exception:
            pass

    def maybe_reload(self) -> bool:
        try:
            m = self.path.stat().st_mtime if self.path.exists() else 0.0
            if m and m > self._mtime:
                self.reload()
                return True
        except Exception:
            pass
        return False

    def get(self, path: str, default=None):
        return deep_get(self._data, path, default)

    def set(self, path: str, value):
        if path:
            deep_set(self._data, path, value)
        else:
            self._data = value
        try:
            CONFIG_PATH.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
            self._mtime = CONFIG_PATH.stat().st_mtime
        except Exception:
            pass
