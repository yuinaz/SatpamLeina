from __future__ import annotations

# -*- coding: utf-8 -*-
"""XP Consistency Overlay (Upstash auto-heal) — v2 (same as v1, safe import)
- Runs once on_ready to unify totals (MAX of v1/v2 keys), recompute label,
  and write learning:status & learning:status_json atomically.
- No side effects on import; respects on_ready bootstrap rule.
"""

import os
import json
import asyncio
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, List, TypedDict, Union, Optional, cast

# Type definitions for XP data structures
class XPMeta(TypedDict, total=False):
    required: int
    current: int

class XPStatusJson(TypedDict):
    label: str
    percent: float
    remaining: int
    senior_total: int
    stage: XPMeta

# Safe discord imports
try:
    from discord.ext import commands  # type: ignore
    has_discord = True
except Exception:
    commands = object  # type: ignore
    has_discord = False

log = logging.getLogger(__name__)

def _upstash_base() -> Optional[str]:
    b = (os.getenv("UPSTASH_REDIS_REST_URL", "") or "").rstrip("/")
    return b or None

def _upstash_auth() -> Optional[str]:
    t = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
    return t or None

def _pipeline(cmds: List[List[str]]) -> tuple[int, Any]:
    base = _upstash_base(); tok = _upstash_auth()
    if not base or not tok:
        return (0, "UPSTASH env missing")
    req = urllib.request.Request(f"{base}/pipeline",
        data=json.dumps(cmds).encode(), method="POST",
        headers={"Authorization": f"Bearer {tok}", "Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = r.read().decode()
            try:
                return (r.getcode(), json.loads(body))
            except Exception:
                return (r.getcode(), body)
    except urllib.error.HTTPError as e:
        try: body = e.read().decode()
        except Exception: body = str(e)
        return (e.code, body)
    except Exception as e:
        return (-1, str(e))

S_NAMES = ("S1","S2","S3","S4","S5","S6","S7","S8")  # type: tuple[str, ...]
S_TH = (0,19000, 35000, 58000, 70000, 96500, 158000, 220000, 262500)  # type: tuple[int, ...]

def _to_int(x: Any) -> int:
    """Convert any value to int safely."""
    try:
        return int(float(str(x).strip()))
    except Exception:
        return 0

def _pick_total(raw_a: int, sj_total: int) -> tuple[int, str]:
    """Pick which total to use based on mode."""
    mode = (os.getenv('XP_AUTOHEAL_MODE','prefer_status_json') or 'prefer_status_json').lower()
    a = int(raw_a or 0); b = int(sj_total or 0)
    if mode == 'prefer_raw':
        return (a if a>0 else b), 'prefer_raw'
    if mode == 'max':
        return max(a,b), 'max'
    if mode == 'min':
        return min(x for x in (a,b) if x>0) if (a>0 or b>0) else 0, 'min'
    # default: prefer_status_json
    return (b if b>0 else a), 'prefer_status_json'

def _calc(total: int) -> tuple[str, str, XPStatusJson]:
    """Calculate XP stage and status."""
    try:
        from ..helpers.xp_total_resolver import stage_from_total  # type: ignore
        lbl, pct, meta_raw = stage_from_total(int(total))
        status = f"{lbl} ({pct}%)"
        # TypedDict is for typing only; construct a plain dict at runtime and
        # annotate it as XPMeta for type-checkers.
        meta: XPMeta = {"required": int(meta_raw.get("required", 1)), "current": int(meta_raw.get("current", 0))}
        j = cast(XPStatusJson, {
            "label": str(lbl),
            "percent": float(pct),
            "remaining": int(max(0, meta["required"] - meta["current"])),
            "senior_total": int(total),
            "stage": meta
        })
        return lbl, status, j
    except Exception:
        # fallback (legacy thresholds)
        idx = max([i for i,t in enumerate(S_TH) if total>=t] or [0])
        cur = S_TH[idx]; nxt = S_TH[idx] if idx==len(S_TH)-1 else S_TH[idx+1]
        pct = 100.0 if nxt<=cur else round(max(0.0, (total-cur)/float(nxt-cur)*100.0), 1)
        rem = max(0, nxt-total)
        label = f"KULIAH-{S_NAMES[idx]}"
        status = f"{label} ({pct}%)"
        j = cast(XPStatusJson, {
            "label": label,
            "percent": float(pct),
            "remaining": int(rem),
            "senior_total": int(total),
            "stage": {"required": nxt, "current": total}
        })
        return label, status, j

async def _heal() -> None:
    """Run XP consistency healing process."""
    base = _upstash_base(); tok = _upstash_auth()
    if not base or not tok:
        log.warning("[xp-autoheal] UPSTASH env missing")
        return
    
    key_a = os.getenv("XP_SENIOR_KEY") or os.getenv("SENIOR_XP_KEY") or "xp:bot:senior_total"
    code, res = _pipeline([["GET",key_a],["GET","learning:status"],["GET","learning:status_json"]])
    if code <= 0:
        log.warning("[xp-autoheal] read failed: %s", res)
        return

    try:
        xp_raw = _to_int(res[0].get("result"))
        status_raw = res[1].get("result") or ""
        json_raw = res[2].get("result") or "{}"
    except Exception:
        xp_raw = 0
        status_raw = ""
        json_raw = "{}"
    
    sj_total = 0
    try:
        _j = json.loads(json_raw)
        sj_total = int(_j.get("senior_total") or 0)
    except Exception:
        sj_total = 0
    
    chosen, mode = _pick_total(xp_raw, sj_total)
    label, status, j = _calc(chosen)
    need = True
    try:
        lbl_s = (status_raw.split(" ",1)[0] if status_raw else "")
        import json as _j2
        lbl_j = _j2.loads(json_raw).get("label","")
        need = (lbl_s!=label) or (lbl_j!=label) or (chosen != xp_raw) or (chosen != sj_total)
    except Exception:
        need = True
    
    if not need:
        log.info("[xp-autoheal] consistent: %s", label)
        return
    
    # Update if needed
    cmds = [
        ["SET", key_a, str(chosen)],
        ["SET", "learning:status", status],
        ["SET", "learning:status_json", json.dumps(j, separators=(',',':'))]
    ]
    code2, res2 = _pipeline(cmds)
    if 200 <= code2 < 300:
        log.info("[xp-autoheal] fixed -> %s (total=%s)", label, chosen)
    else:
        log.warning("[xp-autoheal] write failed: %s %s", code2, res2)

class XPConsistencyOverlay(commands.Cog):  # type: ignore
    """XP consistency overlay cog."""
    def __init__(self, bot: Any = None) -> None:
        self.bot = bot
        # Use non-generic Task typing to avoid typing incompatibilities on older
        # typing backports/environments.
        self._task: Optional[asyncio.Task] = None

    async def on_ready(self) -> None:
        """Handle on_ready event."""
        if os.getenv("XP_DISABLE_AUTOHEAL"): 
            log.info("[xp-autoheal] disabled")
            return
        if self._task is None:
            self._task = asyncio.create_task(self._once())

    async def _once(self) -> None:
        """Run one auto-heal cycle."""
        await asyncio.sleep(2.0)
        try:
            await _heal()
        except Exception as e:
            log.exception("[xp-autoheal] error: %s", e)

async def setup(bot: Any) -> None:
    """Async setup for the cog."""
    try:
        await bot.add_cog(XPConsistencyOverlay(bot))  # type: ignore
        log.info('✅ Loaded cog (async): %s', __name__)
    except Exception as e:
        log.exception('Failed to load XPConsistencyOverlay (async): %s', e)