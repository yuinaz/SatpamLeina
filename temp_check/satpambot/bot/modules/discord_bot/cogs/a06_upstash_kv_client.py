import os
import json
import asyncio
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore


class UpstashClient:
    """
    Minimal Upstash REST client tailored for this bot.
    - Uses /pipeline for safe writes.
    - GET/SET helpers for single keys.
    - Does NOT create keys unintentionally: you control that in callers.
    """

    def __init__(self, url: Optional[str] = None, token: Optional[str] = None, timeout: float = 8.0):
        self.url = (url or os.getenv("UPSTASH_REDIS_REST_URL", "")).rstrip("/")
        self.token = token or os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
        self.timeout = timeout

    def ready(self) -> bool:
        return bool(self.url and self.token and httpx is not None)

    async def _client(self) -> "httpx.AsyncClient":
        timeout = httpx.Timeout(self.timeout)
        headers = {"Authorization": f"Bearer {self.token}"}
        return httpx.AsyncClient(timeout=timeout, headers=headers)

    async def get_raw(self, key: str) -> Optional[str]:
        if not self.ready():
            return None
        async with await self._client() as ac:
            try:
                # Safe GET using path endpoint to avoid query encoding issues
                r = await ac.get(f"{self.url}/get/{httpx.utils.quote(key, safe='')}")
                r.raise_for_status()
                data = r.json()
                res = data.get("result")
                return res
            except Exception:
                return None

    async def set_raw(self, key: str, value: str) -> bool:
        if not self.ready():
            return False
        async with await self._client() as ac:
            try:
                # Use pipeline for set to be consistent
                payload = [["SET", key, value]]
                r = await ac.post(f"{self.url}/pipeline", json=payload)
                r.raise_for_status()
                return True
            except Exception:
                return False

    async def pipeline(self, commands: List[List[str]]) -> bool:
        if not self.ready():
            return False
        async with await self._client() as ac:
            try:
                r = await ac.post(f"{self.url}/pipeline", json=commands)
                r.raise_for_status()
                return True
            except Exception:
                return False


def json_loads_maybe_twice(s: Optional[str]) -> Optional[Any]:
    """
    Upstash GET returns {"result": "<string>"} where the stored value might be JSON.
    It can be double-encoded depending how it was written. We try decode twice.
    """
    if s is None:
        return None
    try:
        v = json.loads(s)
        # If the result is still a string that looks like JSON, try again once.
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return v
        return v
    except Exception:
        return None


def iso_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
async def setup(bot):
    return None
