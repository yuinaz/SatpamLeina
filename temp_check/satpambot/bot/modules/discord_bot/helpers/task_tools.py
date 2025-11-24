
from __future__ import annotations
import asyncio
from typing import Any

def create_task_any(bot: Any, coro):
    try:
        loop = getattr(bot, "loop", None)
        if loop and hasattr(loop, "create_task"):
            return loop.create_task(coro)
    except Exception:
        pass
    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(coro)
    except Exception:
        pass
    try:
        loop = asyncio.get_event_loop()
        return loop.create_task(coro)
    except Exception:
        pass
    try:
        return asyncio.ensure_future(coro)
    except Exception:
        return None
