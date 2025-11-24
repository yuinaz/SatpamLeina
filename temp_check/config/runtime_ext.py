# satpambot/config/runtime_ext.py
from __future__ import annotations
import os, json
from pathlib import Path
from typing import Dict, Any

# We depend on the existing runtime.cfg for precedence (ENV > LOCAL > DEFAULTS as patched).
from . import runtime as _rt

# Heuristic prefixes that we consider as config-ish when harvesting env keys
_PREFIXES = (
    "CHAT_",  "GROQ_", "MAINT_", "NAP_", "STICKER_", "OWNER_", "SELF_", "BOOT_", "BAN_", "METRICS_", "LOG_",
    "DASH_", "FAST_GUARD_", "PHISH_", "THREAD_", "COG_", "PORT", "IMPORTED_ENV_NOTIFY"
)

ROOT = Path(__file__).resolve().parents[2]
CFG_PATH = ROOT / "satpambot_config.local.json"
SECRETS_DIR = ROOT / "secrets"

def _load_local_keys() -> set[str]:
    try:
        data = json.loads(CFG_PATH.read_text(encoding="utf-8"))
        return set(data.keys())
    except Exception:
        return set()

def _env_keys() -> set[str]:
    ks = set()
    for k in os.environ.keys():
        uk = k.upper()
        if uk in _rt.DEFAULTS:
            ks.add(uk)
            continue
        if any(uk.startswith(p) for p in _PREFIXES):
            ks.add(uk)
    return ks

def all_cfg() -> Dict[str, Any]:
    """Return a merged mapping where each value is resolved via runtime.cfg (ENV > LOCAL > DEFAULTS)."""
    keys = set(_rt.DEFAULTS.keys()) | _load_local_keys() | _env_keys()
    out: Dict[str, Any] = {}
    for k in sorted(keys):
        out[k] = _rt.cfg(k)
    return out

def set_secret(name: str, value: str) -> None:
    """Persist secret into secrets/NAME.txt (simple, git-ignorable)."""
    try:
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        p = SECRETS_DIR / f"{name.lower()}.txt"
        p.write_text(value or "", encoding="utf-8")
    except Exception:
        pass
