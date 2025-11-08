
from __future__ import annotations
import os, asyncio, logging
from typing import Optional

log = logging.getLogger(__name__)

def _cfg(key: str, default: str = "") -> str:
    try:
        from satpambot.config.auto_defaults import cfg_str as _cs
        return _cs(key, default)
    except Exception:
        return os.getenv(key, default)

def _first_nonempty(*names: str, default: str = "") -> str:
    for n in names:
        v = _cfg(n, "").strip()
        if v:
            return v
    return default

class UpstashClient:
    def __init__(self):
        url = _first_nonempty("UPSTASH_REDIS_REST_URL", "REDIS_REST_URL", "UPSTASH_URL")
        tok = _first_nonempty("UPSTASH_REDIS_REST_TOKEN", "REDIS_REST_TOKEN", "UPSTASH_TOKEN")
        self.url = url.rstrip("/") if url else ""
        self.token = tok
        self.enabled = bool(self.url and self.token)
        self._httpx = None
        try:
            import httpx  # type: ignore
            self._httpx = httpx
        except Exception:
            self._httpx = None
        log.info("[upstash-client] enabled=%s url=%s", self.enabled, ("..."+self.url[-24:] if self.url else ""))

    async def _aget(self, path: str):
        if os.getenv('LEINA_SHUTTING_DOWN') == '1':
            log.warning('[upstash-client] skip (shutting down) GET %s', path)
            return None
        if not self.enabled:
            return None
        target = f"{self.url}{path}"
        headers = {"Authorization": f"Bearer {self.token}"}
        if self._httpx:
            async with self._httpx.AsyncClient(timeout=20) as cli:
                r = await cli.get(target, headers=headers)
                r.raise_for_status()
                return r.json()
        else:
            import requests  # type: ignore
            def _do():
                rr = requests.get(target, headers=headers, timeout=20)
                rr.raise_for_status()
                return rr.json()
            return await asyncio.to_thread(_do)

    async def _apost(self, path: str):
        if os.getenv('LEINA_SHUTTING_DOWN') == '1':
            log.warning('[upstash-client] skip (shutting down) POST %s', path)
            return None
        if not self.enabled:
            return None
        target = f"{self.url}{path}"
        headers = {"Authorization": f"Bearer {self.token}"}
        if self._httpx:
            async with self._httpx.AsyncClient(timeout=20) as cli:
                r = await cli.post(target, headers=headers)
                r.raise_for_status()
                return r.json()
        else:
            import requests  # type: ignore
            def _do():
                rr = requests.post(target, headers=headers, timeout=20)
                rr.raise_for_status()
                return rr.json()
            return await asyncio.to_thread(_do)

    async def get_raw(self, key: str):
        try:
            d = await self._aget(f"/get/{key}")
            if not isinstance(d, dict): return None
            return d.get("result")
        except Exception as e:
            log.debug("[upstash-client] get_raw fail: %r", e)
            return None

    async def setex(self, key: str, ttl_sec: int, value: str) -> bool:
        try:
            d = await self._apost(f"/set/{key}/{value}?EX={int(ttl_sec)}")
            ok = isinstance(d, dict) and str(d.get("result", "")).upper() == "OK"
            if not ok:
                log.debug("[upstash-client] setex unexpected resp: %r", d)
            return ok
        except Exception as e:
            log.debug("[upstash-client] setex fail: %r", e)
            return False

    async def incrby(self, key: str, n: int) -> bool:
        try:
            d = await self._apost(f"/incrby/{key}/{int(n)}")
            ok = isinstance(d, dict) and "result" in d
            if not ok:
                log.debug("[upstash-client] incrby unexpected resp: %r", d)
            return ok
        except Exception as e:
            log.debug("[upstash-client] incrby fail: %r", e)
            return False
