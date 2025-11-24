from __future__ import annotations

# satpambot/bot/helpers/uptime_state.py
import time
online: bool = False
last_change: float = time.time()

def set_state(v: bool) -> None:
    global online, last_change
    online = bool(v)
    last_change = time.time()

def get_state():
    return {"online": online, "last_change": int(last_change)}
