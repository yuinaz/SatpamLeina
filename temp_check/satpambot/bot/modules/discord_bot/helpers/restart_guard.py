# restart_guard.py — robust, NO-ENV, persistent if /data exists
import json, time, pathlib, os
from typing import Tuple

STATE_DIRS = ["/data/satpambot_state", "/tmp"]
F_GUARD = "restart.lock"

def _state_path(name: str) -> pathlib.Path:
    for d in STATE_DIRS:
        try:
            p = pathlib.Path(d)
            p.mkdir(parents=True, exist_ok=True)
            return p / name
        except Exception:
            continue
    return pathlib.Path("/tmp") / name

GUARD_FILE = _state_path(F_GUARD)
WINDOW_SEC = 240  # 4 minutes

def guard_status() -> Tuple[bool, float | None]:
    p = GUARD_FILE
    try:
        if p.exists():
            return True, time.time() - p.stat().st_mtime
        return False, None
    except Exception:
        return False, None

def mark(reason: str = "unknown") -> bool:
    p = GUARD_FILE
    try:
        p.write_text(json.dumps({"t": time.time(), "reason": reason}, ensure_ascii=False))
        return True
    except Exception:
        return False

def clear() -> bool:
    try:
        _state_path(F_GUARD).unlink(missing_ok=True)
        return True
    except Exception:
        return False

def should_restart() -> Tuple[bool, float | None]:
    exists, age = guard_status()
    return not (exists and age is not None and age < WINDOW_SEC), age
