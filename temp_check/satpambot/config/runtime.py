from __future__ import annotations

# satpambot/config/runtime.py
import os, json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
CFG_PATH = (ROOT / "local.json") if (ROOT / "local.json").exists() else (ROOT / "local.json (fallback: satpambot_config.local.json)")
SECRETS_DIR = ROOT / "secrets"

DEFAULTS: Dict[str, Any] = {
    "PORT": 10000,
    "CHAT_ENABLE": True,
    "CHAT_ALLOW_DM": True,
    "CHAT_ALLOW_GUILD": True,
    "CHAT_MENTIONS_ONLY": False,
    "CHAT_MIN_INTERVAL_S": 8,
    "CHAT_MAX_TOKENS": 256,
    "IMPORTED_ENV_NOTIFY": False,
}

def _read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _write_json(path: Path, data: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
    except Exception:
        pass

_LOCAL = _read_json(CFG_PATH)

_BOOL_KEYS = {
    "COMMANDS_OWNER_ONLY","UPDATE_DM_OWNER","MAINTENANCE_AUTO","NAP_ENABLE","NAP_DM_NOTIF",
    "STICKER_ENABLE","BOOT_DM_ONLINE","SELF_LEARNING_ENABLE","CHAT_ENABLE","CHAT_ALLOW_DM",
    "CHAT_ALLOW_GUILD","CHAT_MENTIONS_ONLY","IMPORTED_ENV_NOTIFY"
}
_INT_KEYS = {"PORT","CHAT_MAX_TOKENS","CHAT_MIN_INTERVAL_S","LLM_TIMEOUT_S"}
_FLOAT_KEYS = {"NAP_CPU_LOW","NAP_CPU_HIGH","NAP_MSG_LOW","NAP_MSG_HIGH","NAP_ADAPT_ALPHA","MAINT_HALF_CPU","MAINT_RESUME_CPU"}

def _parse_bool(v: Any) -> bool:
    if isinstance(v, bool): return v
    s = str(v).strip().lower()
    return s in ("1","true","yes","on","y")

def _coerce(k: str, v: Any) -> Any:
    try:
        if k in _BOOL_KEYS: return _parse_bool(v)
        if k in _INT_KEYS: return int(v)
        if k in _FLOAT_KEYS: return float(v)
    except Exception:
        return v
    return v

def cfg(key: str, default: Any = None) -> Any:
    if key in os.environ:
        return _coerce(key, os.environ[key])
    if key in _LOCAL:
        return _coerce(key, _LOCAL[key])
    if key in DEFAULTS:
        return _coerce(key, DEFAULTS[key])
    return default

def set_cfg(key: str, value: Any) -> None:
    _LOCAL[key] = value
    _write_json(CFG_PATH, _LOCAL)

def get_secret(name: str) -> str | None:
    try:
        sec = (_read_json(CFG_PATH).get("secrets") or {})
        if name in sec and sec[name]:
            return str(sec[name])
    except Exception:
        pass
    try:
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        cand = SECRETS_DIR / f"{name.lower()}.txt"
        if cand.exists():
            return cand.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return os.getenv(name)

_PREFIXES = (
    "CHAT_", "GROQ_", "MAINT_", "NAP_", "STICKER_", "OWNER_", "SELF_", "BOOT_", "BAN_", "METRICS_", "LOG_",
    "DASH_", "FAST_GUARD_", "PHISH_", "THREAD_", "COG_", "PORT", "IMPORTED_ENV_NOTIFY", "LLM_"
)

def _env_keys() -> set[str]:
    ks = set()
    for k in os.environ.keys():
        uk = k.upper()
        if uk in DEFAULTS or any(uk.startswith(p) for p in _PREFIXES):
            ks.add(uk)
    return ks

def _local_keys() -> set[str]:
    try:
        return set(_LOCAL.keys())
    except Exception:
        return set()

def all_cfg() -> Dict[str, Any]:
    keys = set(DEFAULTS.keys()) | _local_keys() | _env_keys()
    out: Dict[str, Any] = {}
    for k in sorted(keys):
        out[k] = cfg(k)
    return out

def set_secret(name: str, value: str) -> None:
    try:
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        p = SECRETS_DIR / f"{name.lower()}.txt"
        p.write_text(value or "", encoding="utf-8")
    except Exception:
        pass
