from __future__ import annotations

# SPDX-License-Identifier: MIT
# Helper for marking and reading restart intent across process restarts.
import os, json, time, pathlib
from typing import Optional, Dict, Any

SENTINEL_PATH = os.environ.get("RESTART_SENTINEL_PATH", "/tmp/satpambot_restart.json")

def mark(reason: str, actor_id: Optional[int] = None, seconds: float = 0.0) -> None:
    """Create a sentinel file so the next process knows a user-initiated restart happened."""
    try:
        pathlib.Path(SENTINEL_PATH).parent.mkdir(parents=True, exist_ok=True)
        data = {"ts": time.time(), "reason": reason, "actor_id": actor_id, "seconds": seconds}
        with open(SENTINEL_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

def pop() -> Optional[Dict[str, Any]]:
    """Return the sentinel dict if present, and remove the file."""
    try:
        with open(SENTINEL_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    try:
        os.remove(SENTINEL_PATH)
    except Exception:
        pass
    return data
