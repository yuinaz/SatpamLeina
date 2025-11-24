from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from typing import Any, Dict

# Path to metrics file; default inside repo's data dir
METRIC_PATH = os.getenv("SHADOW_METRICS_PATH", "data/neuro-lite/observe_metrics.json")
_DIR = os.path.dirname(METRIC_PATH) or "."

log = logging.getLogger(__name__)
_lock = threading.Lock()


def _ensure_dir() -> None:
    try:
        os.makedirs(_DIR, exist_ok=True)
    except Exception as e:
        log.warning("[shadow_metrics] failed to ensure dir %r: %r", _DIR, e)


def _load() -> Dict[str, Any]:
    try:
        with open(METRIC_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        # If file corrupt or unreadable, don't crash bot
        log.warning("[shadow_metrics] load failed (%r); starting fresh", e)
        return {}


def _atomic_write(data: Dict[str, Any]) -> None:
    _ensure_dir()

    # Create unique temp file in same directory for atomic replace
    fd, tmp = tempfile.mkstemp(prefix="observe_metrics.", suffix=".tmp", dir=_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
            f.flush()
            try:
                os.fsync(f.fileno())  # durability
            except Exception:
                # not all fs support fsync
                pass

        # Retry a few times to be Windows/AV friendly
        for attempt in range(5):
            try:
                os.replace(tmp, METRIC_PATH)  # atomic on Windows/Unix
                return
            except PermissionError as e:
                # File might be momentarily locked by AV/indexer
                time.sleep(0.08 * (attempt + 1))
            except FileNotFoundError:
                # If temp vanished (AV), recreate and retry
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except Exception:
                        pass
        # Final fallback
        try:
            with open(METRIC_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        except Exception as e:
            log.warning("[shadow_metrics] fallback write failed: %r", e)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def bump(key: str, value: float, *, user_id: int | None = None) -> None:
    with _lock:
        obj = _load()
        try:
            obj[key] = float(obj.get(key, 0)) + float(value)
        except Exception:
            # If previous value not numeric, overwrite
            obj[key] = float(value)

        if user_id is not None:
            per_user = obj.setdefault("per_user", {})
            sid = str(user_id)
            try:
                per_user[sid] = float(per_user.get(sid, 0)) + float(value)
            except Exception:
                per_user[sid] = float(value)

        _atomic_write(obj)
