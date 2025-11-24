# Config manager (auto)
import os, json, time

CONFIG_PATH = os.getenv("MODULES_CONFIG_FILE", "config/modules.json")
_cache = {"ts": 0, "data": {}}
TTL = 5  # seconds

def _load_from_disk():
    try:
        with open(CONFIG_PATH,"r",encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def load_config(force=False):
    now = time.time()
    if force or now - _cache["ts"] > TTL:
        _cache["data"] = _load_from_disk()
        _cache["ts"] = now
    return dict(_cache["data"])

def save_config(data: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH,"w",encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    _cache["data"] = dict(data)
    _cache["ts"] = time.time()

def get_flag(key: str, default=None):
    cfg = load_config()
    return cfg.get(key, os.getenv(key, default))
