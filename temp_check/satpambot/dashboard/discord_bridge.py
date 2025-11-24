# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio, time
from typing import Any, Dict

_bot = None
_last_ok_ts = 0.0

def set_bot(bot):  # dipanggil dari init bot
    global _bot
    _bot = bot

def get_bot():
    return _bot

def is_ready() -> bool:
    try:
        return bool(_bot and _bot.is_ready())
    except Exception:
        return False

def _run_coro_sync(coro, timeout: float = 2.5):
    if not _bot or not getattr(_bot, "loop", None):
        return None
    fut = asyncio.run_coroutine_threadsafe(coro, _bot.loop)
    try:
        return fut.result(timeout=timeout)
    except Exception:
        try: fut.cancel()
        except Exception: pass
        return None

async def _collect_async() -> Dict[str, Any]:
    b = _bot
    data = {"guild_count":0,"channel_count":0,"thread_count":0,"member_count":0,"online_count":0,"latency_ms":0}
    if not b:
        return data
    try:
        guilds = list(getattr(b, "guilds", []) or [])
        data["guild_count"] = len(guilds)
        for g in guilds:
            try: data["channel_count"] += len(getattr(g,"channels",[]) or [])
            except Exception: pass
            try:
                for ch in (getattr(g,"text_channels",[]) or []):
                    try: data["thread_count"] += len(getattr(ch,"threads",[]) or [])
                    except Exception: pass
            except Exception: pass
            # member_count & online
            mc = getattr(g, "member_count", None)
            if isinstance(mc, int): data["member_count"] += mc
            try:
                for m in (getattr(g,"members",[]) or []):
                    st = getattr(m,"status",None); sval = getattr(st,"value",st)
                    if str(sval) in ("online","idle","dnd"): data["online_count"] += 1
            except Exception: pass
        try: data["latency_ms"] = int(float(getattr(b,"latency",0.0))*1000.0)
        except Exception: pass
    except Exception:
        pass
    return data

def get_metrics(timeout: float = 2.5) -> Dict[str, Any]:
    global _last_ok_ts
    if not is_ready():
        return {"ok": False, "reason": "not_ready"}
    data = _run_coro_sync(_collect_async(), timeout=timeout) or {}
    if data: _last_ok_ts = time.time()
    data.update({"ok": bool(data), "last_ok_ts": int(_last_ok_ts), "ts": int(time.time())})
    return data or {"ok": False, "reason": "collect_failed"}
