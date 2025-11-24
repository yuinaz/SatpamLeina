
from __future__ import annotations
import os, json, logging, inspect, asyncio, re
from typing import Optional, Tuple, List, Any
from pathlib import Path

log = logging.getLogger(__name__)

_LADDER_WARNED = False

def _cfg_str(key: str, default: str) -> str:
    try:
        from satpambot.config.auto_defaults import cfg_str as _cs
        return _cs(key, default)
    except Exception:
        return os.getenv(key, default)

try:
    from ..helpers.upstash_rest import cmd as _upstash_cmd  # type: ignore
except Exception:
    _upstash_cmd = None  # type: ignore

def _call_cmd(*args, **kwargs):
    if _upstash_cmd is None:
        return {"result": None}
    return _upstash_cmd(*args, **kwargs)

def _parse_result(obj) -> Optional[str]:
    try:
        if isinstance(obj, dict):
            return obj.get("result")
        return obj
    except Exception:
        return None

async def _get_status_json() -> Optional[dict]:
    try:
        r = _call_cmd("GET", "learning:status_json")
        if inspect.isawaitable(r):
            r = await r
        s = _parse_result(r)
        if not s:
            return None
        return json.loads(s)
    except Exception:
        return None

async def resolve_senior_total() -> Optional[int]:
    sj = await _get_status_json()
    if sj and isinstance(sj.get("senior_total"), (int, float, str)):
        try:
            return int(sj["senior_total"])
        except Exception:
            pass
    key = _cfg_str("XP_SENIOR_KEY", "xp:bot:senior_total")
    try:
        r = _call_cmd("GET", key)
        if inspect.isawaitable(r):
            r = await r
        s = _parse_result(r)
        if s is None:
            return None
        return int(s)
    except Exception as e:
        log.warning("[xp-resolver] read %s fail: %s", key, e)
        return None

_DEFAULTS = [('S1', 19000), ('S2', 35000), ('S3', 58000), ('S4', 70000), ('S5', 96500), ('S6', 158000), ('S7', 220000), ('S8', 262500)]
_DEFAULT_CAP = 262500

def _ladder_path() -> Path:
    here = Path(__file__).resolve()
    for _ in range(10):
        cand = (here.parent / ("../" * _) / "data/ladder.json").resolve()
        if cand.exists():
            return cand
    return Path("data/ladder.json")

def _norm_pairs(pairs: List[tuple[str,int]]) -> List[tuple[str,int]]:
    items = []
    for k,v in pairs:
        m = re.search(r"S(\d+)", k, re.I)
        if not m:
            continue
        try:
            items.append((int(m.group(1)), f"S{m.group(1)}", int(v)))
        except Exception:
            continue
    items.sort()
    return [(lab, val) for _, lab, val in items]


def _needs_pairs_to_kuliah_starts(pairs: List[tuple[str,int]]) -> List[tuple[str,int]]:
    """Convert per-stage *needs* (e.g., S1=19000, S2=35000, ...)
    into KULIAH-only cumulative *starts*:
        S1 -> 0
        S2 -> S1
        S3 -> S1+S2
        ...
    We intentionally do NOT include SMP/SMA in this start offset so that
    displayed totals align with Upstash \"start_total\" semantics.
    """
    items = _norm_pairs(pairs)
    starts: List[tuple[str,int]] = []
    acc = 0
    for lab, need in items:
        starts.append((lab, acc))
        try:
            acc += int(need)
        except Exception:
            pass
    return starts

def _ladder_from_dict(d: dict) -> List[tuple[str,int]]:
    # Try nested senior->KULIAH first
    try:
        if isinstance(d.get('senior'), dict):
            for kk in d['senior'].keys():
                if kk.lower() == 'kuliah':
                    return _norm_pairs([(k, d['senior'][kk][k]) for k in d['senior'][kk].keys()])
    except Exception:
        pass
    # Then try direct KULIAH on current level
    src = None
    for kk in list(d.keys()):
        if kk.lower() == 'kuliah':
            src = d[kk]
            break
    if src is None:
        src = d
    if isinstance(src, dict):
        return _norm_pairs([(k, src[k]) for k in src.keys()])
    return []

def _ladder_from_list(lst: list) -> List[tuple[str,int]]:
    pairs = []
    for it in lst:
        if isinstance(it, dict):
            lbl = it.get("label") or it.get("stage") or it.get("name")
            start = it.get("start_total", it.get("start"))
            if lbl is not None and start is not None:
                pairs.append((str(lbl), int(start)))
    return _norm_pairs(pairs)

def load_kuliah_thresholds() -> List[tuple[str,int]]:
    global _LADDER_WARNED
    try:
        p = _ladder_path()
        j = json.loads(p.read_text(encoding="utf-8"))
        pairs: List[tuple[str,int]] = []
        if isinstance(j, dict):
            pairs = _ladder_from_dict(j)
        elif isinstance(j, list):
            pairs = _ladder_from_list(j)
        if not pairs:
            if not _LADDER_WARNED:
                log.warning("[xp-resolver] ladder empty/invalid; using defaults")
                _LADDER_WARNED = True
            # Interpret defaults as *needs* and convert to starts
            return _needs_pairs_to_kuliah_starts(_DEFAULTS.copy())
        # Convert declared per-stage needs into KULIAH-only cumulative starts
        return _needs_pairs_to_kuliah_starts(pairs)
    except Exception:
        # Fallback to defaults-as-needs
        return _needs_pairs_to_kuliah_starts(_DEFAULTS.copy())

def stage_from_total(total: int) -> tuple[str, float, dict]:
    try:
        total = max(0, int(total))
    except Exception:
        total = 0
    starts = load_kuliah_thresholds()  # list[(label, start)]
    if not starts:
        starts = _needs_pairs_to_kuliah_starts(_DEFAULTS.copy())
    # Compute cap as last start + last need (approx width = delta last-two starts)
    if len(starts) >= 2:
        last_start = starts[-1][1]
        prev_start = starts[-2][1]
        width = max(1000, last_start - prev_start)
        cap = last_start + width
    else:
        cap = max(1000, starts[0][1] + 1000) if starts else 1000
    current_label, current_start = starts[0] if starts else ("S1", 0)
    next_start = cap
    for (lab, st) in starts:
        if total >= st:
            current_label, current_start = lab, st
        else:
            next_start = st
            break
    if total >= next_start:
        pct = 100.0; rem = 0
    else:
        span = max(1, next_start - current_start)
        pct = round(max(0.0, min(100.0, 100.0 * (total - current_start) / float(span))), 1)
        rem = max(0, next_start - total)
    meta = {"start_total": int(current_start), "required": int(max(1, next_start - current_start)), "current": int(max(0, total - current_start))}
    return f"KULIAH-{current_label}", float(pct), meta

async def stage_preferred() -> tuple[str, float, dict]:
    sj = await _get_status_json()
    if sj and isinstance(sj.get("label"), str) and sj["label"].startswith("KULIAH-"):
        try:
            total = int(sj.get("senior_total", 0))
        except Exception:
            total = 0
        st = sj.get("stage") or {}
        try:
            start = int(st.get("start_total", 0))
            req   = int(st.get("required", 1))
        except Exception:
            start, req = 0, 1
        cur = max(0, total - start)
        try:
            pct = max(0.0, min(100.0, 100.0 * (cur / max(1, req))))
        except Exception:
            pct = float(sj.get("percent", 0.0) or 0.0)
        meta = {"start_total": start, "required": req, "current": cur}
        return sj["label"], float(pct), meta
    total = await resolve_senior_total() or 0
    return stage_from_total(int(total))
