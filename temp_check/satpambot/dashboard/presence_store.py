from __future__ import annotations

import time
_state = {
    "guilds": 0, "members": 0, "channels": 0, "threads": 0,
    "online": 0, "latency_ms": 0, "updated": 0
}
def set_stats(d: dict) -> None:
    _state.update({k: d[k] for k in _state.keys() & d.keys()})
    _state["updated"] = int(time.time())
def get_stats() -> dict:
    return dict(_state)
