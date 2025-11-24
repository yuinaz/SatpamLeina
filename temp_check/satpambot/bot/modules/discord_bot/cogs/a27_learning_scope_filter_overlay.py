# Overlay: Learning scope filter at pinned-memory stage
import importlib, logging
from typing import Any, Dict, List

log = logging.getLogger(__name__)

def _cfg(key: str, default=None):
    try:
        from satpambot.config.runtime import cfg
        v = cfg(key)
        return default if v is None else v
    except Exception:
        return default

def _as_set_ints(v) -> "set[int]":
    out = set()
    if isinstance(v, (list, tuple)):
        for x in v:
            try: out.add(int(x))
            except: pass
    return out

def _is_thread_like(item: Dict[str, Any]) -> bool:
    # Heuristik: cek flag/tipe yang umum
    t = str(item.get("channel_type", "")).lower()
    if "thread" in t: return True
    if item.get("is_thread") is True: return True
    # Parent id menandakan thread di bawah parent channel
    if item.get("parent_id") and item.get("channel_id") and item["parent_id"] != item["channel_id"]:
        # tidak selalu thread, tapi aman dianggap thread untuk filter
        return True
    return False

def _is_forum_like(item: Dict[str, Any]) -> bool:
    t = str(item.get("channel_type", "")).lower()
    if "forum" in t: return True
    if item.get("is_forum") is True: return True
    return False

def _filter_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    scope = str(_cfg("LEARN_SCOPE", "denylist")).lower()
    wl = _as_set_ints(_cfg("LEARN_WHITELIST_CHANNELS", []))
    bl = _as_set_ints(_cfg("LEARN_BLACKLIST_CHANNELS", []))
    bc = _as_set_ints(_cfg("LEARN_BLACKLIST_CATEGORIES", []))
    scan_pub_thr = bool(_cfg("LEARN_SCAN_PUBLIC_THREADS", True))
    scan_prv_thr = bool(_cfg("LEARN_SCAN_PRIVATE_THREADS", True))
    scan_forum   = bool(_cfg("LEARN_SCAN_FORUMS", True))

    out = []
    for it in items:
        cid = it.get("channel_id")
        cat = it.get("category_id") or it.get("guild_category_id")
        try:
            icid = int(cid) if cid is not None else None
            icat = int(cat) if cat is not None else None
        except Exception:
            icid, icat = cid, cat

        # category denylist
        if icat in bc:
            continue

        # threads/forums toggle
        if _is_forum_like(it) and not scan_forum:
            continue
        if _is_thread_like(it):
            # "public/private" detection tidak selalu tersedia; pakai hint kalau ada
            is_private = bool(it.get("is_private_thread", False))
            if is_private and not scan_prv_thr:
                continue
            if (not is_private) and not scan_pub_thr:
                continue

        # scope decision
        if scope == "allowlist":
            if icid not in wl:
                continue
        elif scope == "denylist":
            if icid in bl:
                continue
        # scope == "all" => pass

        out.append(it)
    return out

def _wrap():
    try:
        mem = importlib.import_module("satpambot.bot.modules.discord_bot.helpers.memory_upsert")
    except Exception as e:
        log.warning("[scope_filter] cannot import memory_upsert: %r", e); return
    orig = getattr(mem, "upsert_pinned_memory", None)
    if not callable(orig):
        log.warning("[scope_filter] upsert_pinned_memory not found"); return

    async def wrapped(*args, **kwargs):
        # Extract payload
        payload = kwargs.get("payload", None)
        if payload is None and len(args) >= 2:
            payload = args[1]
        # Filter if structure is as expected
        try:
            items = payload.get("items") if isinstance(payload, dict) else None
        except Exception:
            items = None

        if isinstance(items, list):
            before = len(items)
            items2 = _filter_items(items)
            after = len(items2)
            if after != before:
                try:
                    payload["items"] = items2
                except Exception:
                    pass
            log.info("[scope_filter] items %s -> %s (scope=%s)", before, after, _cfg("LEARN_SCOPE","denylist"))

        return await orig(*args, **kwargs)

    setattr(mem, "upsert_pinned_memory", wrapped)
    log.info("[scope_filter] wrapper installed at memory_upsert.upsert_pinned_memory")

_wrap()
async def setup(bot):
    return None
