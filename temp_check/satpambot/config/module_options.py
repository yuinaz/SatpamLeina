from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any, Dict

DEFAULTS: Dict[str, Any] = {
    "OWNER_USER_ID": 228126085160763392,
    "LOG_CHANNEL_ID": 1400375184048787566,
    "LEARNING_QNA_CHANNEL_ID": 1426571542627614772,
    "PROGRESS_THREAD_ID": 1425400701982478408,
    "LEARNING_PROGRESS_THREAD_ID": 1426397317598154844,
    "PUBLIC_MODE_ENABLE": False,
    "INTERVIEW_APPROVED": False,
    "INTERVIEW_CHANNEL_ID": 1426571542627614772,
    "DM_MUZZLE": "owner",
    "AUTO_DELETE_EXEMPT_CHANNEL_IDS": "1426571542627614772",
    "AUTO_DELETE_EXEMPT_THREAD_IDS": "1425400701982478408 1426397317598154844",
    "GOV_MIN_DAYS": 2,
    "GOV_MIN_XP": 2500,
    "GOV_MATURE_ERR_RATE": 0.03,
    "GOV_REQUIRE_QNA_APPROVAL": True,
    "TEXT_ACTIVITY_PERIOD_SEC": 300,
    "TEXT_ACTIVITY_START_SEC": 30,
    "SLANG_TEXT_PERIOD_SEC": 300,
    "SLANG_TEXT_START_SEC": 40,
    "SLANG_PHISH_PERIOD_SEC": 300,
    "SLANG_PHISH_START_SEC": 35,
    "SLANG_PER_CHANNEL": 200,
    "SLANG_TOTAL_BUDGET": 1000,
    "SLANG_SKIP": 8,
    "PHISH_PER_CHANNEL": 200,
    "PHISH_TOTAL_BUDGET": 1000,
    "PHISH_SKIP": 8,
    "SEARCH_PROVIDER": "auto",
    "SEARCH_MAX_RESULTS": 5,
    "SEARCH_OWNER_ONLY": True,
    "GROQ_MODEL_CANDIDATES": "llama-3.1-8b-instant llama-3.1-70b-versatile mixtral-8x7b-32768 gemma2-9b-it",
    "ALERT_COALESCE_WINDOW_SEC": 60,
    "ALERT_COALESCE_MAX_LINES": 15,
    "OWNER_NOTIFY_THREAD_NAME": "Leina Alerts",
    "PERIODIC_STATUS_SEC": 1200,
    "LOG_SAMPLE_RATE": 3,
    "PUBLIC_REPLY_COOLDOWN_SEC": 8,
    "PUBLIC_MAX_CONCURRENT": 2,
    "PUBLIC_BURST": 3,
    "WRITE_BACK_LOCAL_JSON": True,
    "ENV_READ_ENABLE": False,

    # Weekly random XP event
    "WEEKLY_XP_EVENT_ENABLE": True,
    "WEEKLY_XP_MIN": 10,
    "WEEKLY_XP_MAX": 100,
    "WEEKLY_XP_APPLY_TO": "junior",  # 'junior' | 'senior' | 'both'
}
LOCAL_FILES = ["local.json", "satpambot_config.local.json", "config/local.json"]

class ModuleOptions:
    def __init__(self) -> None:
        self.root = Path(__file__).resolve().parents[3]
        self.defaults = dict(DEFAULTS)
        self.local = self._load_local_json()
        if self.get_bool("WRITE_BACK_LOCAL_JSON", True):
            try:
                merged = {**self.defaults, **self.local}
                (self.root/"local.json").write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
        if self.get_bool("ENV_READ_ENABLE", False):
            self._apply_env_overlay()
    def _load_local_json(self) -> Dict[str, Any]:
        for name in LOCAL_FILES:
            p = self.root / name
            if p.exists():
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    return {}
        return {}
    def _apply_env_overlay(self) -> None:
        for k in list(self.defaults.keys()):
            v = os.getenv(k)
            if v is None:
                continue
            self.local[k] = self._coerce_type(k, v)
    def _coerce_type(self, key: str, value: Any) -> Any:
        if key in self.defaults:
            dv = self.defaults[key]
            if isinstance(dv, bool):
                s = str(value).strip().lower()
                return s in ("1","true","t","yes","y","on")
            if isinstance(dv, int) and not isinstance(value, bool):
                try:
                    return int(str(value).strip())
                except Exception:
                    return dv
        return value
    def get(self, key: str, default: Any=None) -> Any:
        if key in self.local:
            return self.local[key]
        if key in self.defaults:
            return self.defaults[key]
        return default
    def get_int(self, key: str, default: int=0) -> int:
        v = self.get(key, default)
        # tolerate strings like "30," or " 120 " or floats "300.0"
        try:
            if isinstance(v, (int, float)):
                return int(v)
            s = str(v).strip()
            s = s.rstrip(",")              # drop trailing commas
            s = s.replace("_", "").replace(" ", "")
            try:
                return int(s)
            except Exception:
                return int(float(s))
        except Exception:
            return default
    def get_bool(self, key: str, default: bool=False) -> bool:
        v = self.get(key, default)
        if isinstance(v, bool): return v
        s = str(v).strip().lower()
        return s in ("1","true","t","yes","y","on")
    def get_list(self, key: str, sep: str=" ,") -> list[str]:
        v = self.get(key, "")
        if isinstance(v, (list, tuple)):
            return [str(x) for x in v]
        s = str(v or "").replace(",", " ")
        return [t for t in s.split() if t]
_opts = ModuleOptions()
def opt(key: str, default: Any=None) -> Any: return _opts.get(key, default)
def opt_int(key: str, default: int=0) -> int: return _opts.get_int(key, default)
def opt_bool(key: str, default: bool=False) -> bool: return _opts.get_bool(key, default)
def opt_list(key: str) -> list[str]: return _opts.get_list(key)
