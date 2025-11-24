
import os
import json
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone

# Flexible source untuk progress:
# 1) ENV PROGRESS_JSON (default: "data/learning_progress.json")
# 2) Import fungsi dari modul learning_progress jika ada: get_overall_progress()
# 3) ENV PROGRESS_VALUE (0.0 - 1.0) untuk override manual (mis. Render)
#
# State runtime ditaruh di memori (fallback) agar bisa toggle tanpa restart.
_RUNTIME_STATE = {"public_open": False, "open_request_sent": False}

@dataclass
class ProgressInfo:
    ratio: float = 0.0        # 0.0..1.0
    accuracy: float = 0.0     # 0.0..1.0
    samples: int = 0
    last_updated: Optional[str] = None  # ISO8601
    
def _load_from_json() -> Optional[ProgressInfo]:
    path = os.getenv("PROGRESS_JSON", "data/learning_progress.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ratio = float(data.get("progress_ratio") or data.get("progress") or 0.0)
        accuracy = float(data.get("shadow_accuracy") or data.get("accuracy") or ratio)
        samples = int(data.get("samples") or data.get("events_seen") or 0)
        last_updated = data.get("last_updated") or datetime.now(timezone.utc).isoformat()
        return ProgressInfo(ratio=ratio, accuracy=accuracy, samples=samples, last_updated=last_updated)
    except Exception:
        return None

def _load_from_module() -> Optional[ProgressInfo]:
    try:
        from satpambot.bot.modules.discord_bot.cogs.learning_progress import get_overall_progress  # type: ignore
        info = get_overall_progress()
        # Diharapkan mengembalikan dict mirip {"ratio":..,"accuracy":..,"samples":..}
        ratio = float(info.get("ratio", 0.0))
        accuracy = float(info.get("accuracy", ratio))
        samples = int(info.get("samples", 0))
        last_updated = info.get("last_updated")
        return ProgressInfo(ratio=ratio, accuracy=accuracy, samples=samples, last_updated=last_updated)
    except Exception:
        return None

def _load_from_env() -> Optional[ProgressInfo]:
    try:
        val = os.getenv("PROGRESS_VALUE")
        if val is None:
            return None
        ratio = float(val)
        return ProgressInfo(ratio=ratio, accuracy=ratio, samples=0, last_updated=datetime.now(timezone.utc).isoformat())
    except Exception:
        return None

def get_progress() -> ProgressInfo:
    return _load_from_env() or _load_from_module() or _load_from_json() or ProgressInfo()

def required_ratio() -> float:
    try:
        return float(os.getenv("PUBLIC_MIN_PROGRESS", "1.0"))
    except Exception:
        return 1.0

def is_public_allowed() -> bool:
    # Runtime gate bisa override sementara (mis. DM command set True/False)
    if _RUNTIME_STATE.get("public_open"):
        return True
    # Env fallback (SILENT_PUBLIC=1 artinya blok)
    if os.getenv("SILENT_PUBLIC", "1") not in ("0", "false", "False"):
        return False
    # Jika SILENT_PUBLIC=0, tetap cek threshold supaya aman
    prog = get_progress()
    return prog.ratio >= required_ratio() and prog.accuracy >= required_ratio()

def set_public_open(value: bool) -> None:
    _RUNTIME_STATE["public_open"] = bool(value)

def get_public_open() -> bool:
    return bool(_RUNTIME_STATE.get("public_open", False))

def set_open_request_sent(value: bool) -> None:
    _RUNTIME_STATE["open_request_sent"] = bool(value)

def get_open_request_sent() -> bool:
    return bool(_RUNTIME_STATE.get("open_request_sent", False))
