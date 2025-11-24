from __future__ import annotations

import asyncio, logging, time
from typing import Dict, Any, Tuple, List
from satpambot.config.local_cfg import cfg_int, cfg
log = logging.getLogger(__name__)
WINDOW = int(cfg_int("ALERT_COALESCE_WINDOW_SEC", 60) or 60)
MAX_LINES = int(cfg_int("ALERT_COALESCE_MAX_LINES", 15) or 15)
THREAD_NAME = cfg("OWNER_NOTIFY_THREAD_NAME", "Leina Alerts") or "Leina Alerts"
_state_lock = asyncio.Lock()
_STATE: Dict[Tuple[int,int,str], Dict[str, Any]] = {}
def _squash_text(content, embed, embeds) -> str:
    parts: List[str] = []
    if content: parts.append(str(content))
    for e in ([embed] if embed else []) + (embeds or []):
        try:
            t = (getattr(e, "title", "") or "").strip()
            d = (getattr(e, "description", "") or "").strip()
            s = (t + "\n" + d).strip()
            if s: parts.append(s)
        except Exception: pass
    seen, out = set(), []
    for ln in "\n".join(parts).splitlines():
        k = ln.strip()
        if not k or k in seen: continue
        seen.add(k); out.append(k)
    return "\n".join(out)
def _install():
    try:
        mod = __import__("satpambot.bot.modules.discord_bot.cogs.a03_owner_notify_redirect_thread", fromlist=["*"])
        original = getattr(mod, "_redirect_to_thread", None)
        if not callable(original): return
        async def _orig_send(channel=None, thread=None, content=None):
            return await original(content=content, channel=channel, thread=thread)
        setattr(mod, "_orig_send_to_thread", _orig_send)
        async def wrapped(*, content=None, embed=None, embeds=None, files=None, **kw):
            channel, thread = kw.get("channel"), kw.get("thread")
            gid = int(getattr(getattr(channel, "guild", None), "id", 0) or 0)
            cid = int(getattr(channel, "id", 0) or 0)
            key = (gid, cid, THREAD_NAME)
            txt = _squash_text(content, embed, embeds)
            if not txt: return
            async with _state_lock:
                st = _STATE.get(key) or {"buf": [], "ts": 0.0, "msg": None}
                st["buf"].append(txt); _STATE[key] = st
            async def _flush():
                async with _state_lock:
                    st = _STATE.get(key)
                    if not st or not st["buf"]: return
                    lines = st["buf"][-MAX_LINES:]
                    body = "**Alert (coalesced)** — last {} lines:\n".format(len(lines)) + "\n".join(f"• {l}" for l in lines)
                    try:
                        if st["msg"] is None:
                            m = await _orig_send(channel=channel, thread=thread, content=body); st["msg"] = m
                        else:
                            try: await st["msg"].edit(content=body)
                            except Exception:
                                m = await _orig_send(channel=channel, thread=thread, content=body); st["msg"] = m
                    except Exception as e: log.debug("[alert_coalescer] flush failed: %s", e)
                    finally: st["buf"].clear(); st["ts"]=time.time(); _STATE[key]=st
            asyncio.create_task(asyncio.sleep(WINDOW)); asyncio.create_task(_flush()); return
        setattr(mod, "_redirect_to_thread", wrapped); log.info("[alert_coalescer] installed window=%s lines=%s", WINDOW, MAX_LINES)
    except Exception as e: log.warning("[alert_coalescer] install failed: %s", e)
_install()