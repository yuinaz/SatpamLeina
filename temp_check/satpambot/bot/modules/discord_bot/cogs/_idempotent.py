"""
Helpers to make cogs idempotent (avoid double setup) and to coalesce bursty logs.
"""
from __future__ import annotations

import asyncio, time
from typing import Any, Optional, Callable, Dict

def set_once_flag(obj: Any, name: str) -> bool:
    if getattr(obj, name, False):
        return False
    setattr(obj, name, True)
    return True

class TTLSet:
    def __init__(self, ttl_seconds: float = 600.0, maxlen: int = 4096):
        self._ttl = ttl_seconds
        self._maxlen = maxlen
        self._store: Dict[int, float] = {}

    def __contains__(self, key: int) -> bool:
        now = time.time()
        self._purge(now)
        return key in self._store

    def add(self, key: int) -> None:
        now = time.time()
        self._purge(now)
        if len(self._store) >= self._maxlen:
            oldest = min(self._store, key=self._store.get)
            self._store.pop(oldest, None)
        self._store[key] = now + self._ttl

    def _purge(self, now: Optional[float] = None) -> None:
        if now is None:
            now = time.time()
        expired = [k for k, exp in self._store.items() if exp <= now]
        for k in expired:
            self._store.pop(k, None)

class LogCoalescer:
    def __init__(self, emit_fn: Callable[[str], Any], delay: float = 2.0,
                 singular: str = "1 event",
                 plural: str = "{n} events"):
        self._emit_fn = emit_fn
        self._delay = delay
        self._singular = singular
        self._plural = plural
        self._n = 0
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def bump(self) -> None:
        async with self._lock:
            self._n += 1
            if self._task is None:
                self._task = asyncio.create_task(self._flush())

    async def _flush(self) -> None:
        try:
            await asyncio.sleep(self._delay)
            n = self._n
            self._n = 0
            self._task = None
            if n <= 0:
                return
            if n == 1:
                self._emit_fn(self._singular)
            else:
                self._emit_fn(self._plural.format(n=n))
        except Exception:
            self._task = None