from __future__ import annotations

from typing import Any, Dict

_socketio = None

def set_socketio(sio):
    global _socketio
    _socketio = sio

def emit(channel: str, payload: Dict[str, Any], room: str | None = None):
    if _socketio:
        try:
            if room:
                _socketio.emit(channel, payload, to=room)
            else:
                _socketio.emit(channel, payload, broadcast=True)
        except Exception:
            pass
