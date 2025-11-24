# -*- coding: utf-8 -*-
"""
a00_qna_allowlist_bridge_overlay
- Monkeypatches QnA overlay allowlist to include:
  * ENV QNA_CHANNEL_ALLOWLIST (original behavior)
  * LEARN_CHANNEL_ID (always)
  * governor:public_channels_json from Upstash (dynamic, persisted)
- Lightweight: on-demand fetch with short TTL cache; no tight loops.
"""
import os, time, json, logging, asyncio
from typing import List
log = logging.getLogger(__name__)

QNA_MOD = "satpambot.bot.modules.discord_bot.cogs.a24_autolearn_qna_autoreply_fix_overlay"

def _parse_ints(s: str) -> List[int]:
    out = []
    for p in (s or "").replace(";",",").split(","):
        p = p.strip()
        if p.isdigit():
            out.append(int(p))
    return out

class _UpstashMini:
    def __init__(self):
        self.base = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
        self.enabled = bool(self.base and self.token and os.getenv("KV_BACKEND", "upstash_rest") == "upstash_rest")
        try:
            import aiohttp
            self._aiohttp = aiohttp
        except Exception:
            self._aiohttp = None
        self._cache = (0, [])  # (ts, list)

    async def get_public_channels(self) -> List[int]:
        # cached for 300s
        now = time.time()
        ts, lst = self._cache
        if now - ts < 300 and lst:
            return lst
        if not (self.enabled and self._aiohttp):
            return lst or []
        url = f"{self.base}/get/governor:public_channels_json"
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            async with self._aiohttp.ClientSession() as s:
                async with s.get(url, headers=headers, timeout=6) as r:
                    data = await r.json(content_type=None)
                    res = data.get("result") or "[]"
                    arr = json.loads(res)
                    out = []
                    for x in arr:
                        try: out.append(int(x))
                        except Exception: pass
                    self._cache = (now, out)
                    return out
        except Exception as e:
            log.warning("[qna-allowlist-bridge] fetch failed: %r", e)
            return lst or []
async def setup(bot):
    # monkeypatch target function
    try:
        import importlib
        mod = importlib.import_module(QNA_MOD)
    except Exception as e:
        log.warning("[qna-allowlist-bridge] can't import QnA module: %r", e)
        return
    us = _UpstashMini()
    learn_id = int(os.getenv("LEARN_CHANNEL_ID", "1426571542627614772"))
    env_allow = _parse_ints(os.getenv("QNA_CHANNEL_ALLOWLIST",""))

    async def _channels_allowlist_new() -> List[int]:
        dyn = await us.get_public_channels()
        # union
        return sorted(set(env_allow + [learn_id] + dyn))

    # Patch: support both sync/async getters
    def _channels_allowlist_sync() -> List[int]:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return loop.create_task(us.get_public_channels())  # will not be awaited here
        except Exception:
            pass
        try:
            dyn = asyncio.run(us.get_public_channels())
        except Exception:
            dyn = []
        return sorted(set(env_allow + [learn_id] + dyn))

    # Prefer returning sync function name expected by QnA (if exists)
    if hasattr(mod, "_channels_allowlist"):
        # Replace with a lightweight wrapper that tries async path if awaited
        # We expose a sync function to match original signature but do minimal async hop internally.
        mod._channels_allowlist = _channels_allowlist_sync
        log.info("[qna-allowlist-bridge] _channels_allowlist patched (sync wrapper)")
    else:
        # Fallback: attach as attr (module might pick it up dynamically)
        setattr(mod, "_channels_allowlist", _channels_allowlist_sync)
        log.info("[qna-allowlist-bridge] _channels_allowlist set")

def setup(bot):
    try:
        import asyncio
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
        if loop and loop.is_running():
            return loop.create_task(setup(bot))
        else:
            return asyncio.run(setup(bot))
    except Exception:
        return None
