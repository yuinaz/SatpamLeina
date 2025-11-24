
"""Compilation-safe guard helper for QnAAutoLearnScheduler.

Usage (somewhere in your scheduler setup code):
    from satpambot.bot.modules.discord_bot.cogs._patch_snippets.qna_scheduler_emit_guard import apply_guard
    apply_guard(scheduler_instance, default_interval=180)

This module does **not** execute network operations at import time.
It only patches the provided scheduler instance when `apply_guard` is called.
"""
from __future__ import annotations
import logging, time
from typing import Any, Optional

log = logging.getLogger(__name__)

def _ensure_int(v: Any, default: int) -> int:
    try:
        iv = int(v)
        return iv if iv > 0 else default
    except Exception:
        return default

def apply_guard(sched: Any, default_interval: int = 180, jitter: int = 0) -> bool:
    """Patch a QnAAutoLearnScheduler-like object to ensure safe emission rules.

    - Ensure `interval_sec` exists and is a positive int (fallback to `default_interval`).
    - Ensure `emit_enabled` boolean exists (default True).
    - Optionally set `interval_jitter` if `jitter` > 0.
    - Inject `can_emit(now=None)` method that respects `interval_sec` and `last_emit_at`.
    """
    if sched is None:
        return False

    # Normalize interval
    if not hasattr(sched, "interval_sec") or not isinstance(getattr(sched, "interval_sec"), (int, float)) or getattr(sched, "interval_sec") <= 0:
        sched.interval_sec = _ensure_int(getattr(sched, "interval_sec", None), default_interval)
        log.warning("[qna_sched_guard] set interval_sec=%s", sched.interval_sec)

    # Enable flag
    if not hasattr(sched, "emit_enabled"):
        sched.emit_enabled = True

    # Optional jitter field (not enforced here, just provided)
    if jitter and not hasattr(sched, "interval_jitter"):
        try:
            sched.interval_jitter = int(jitter)
        except Exception:
            pass

    # Inject can_emit helper
    def can_emit(now: Optional[float] = None) -> bool:
        if not getattr(sched, "emit_enabled", True):
            return False
        try:
            now_ts = float(now) if now is not None else time.time()
        except Exception:
            now_ts = time.time()
        try:
            last = float(getattr(sched, "last_emit_at", 0) or 0.0)
        except Exception:
            last = 0.0
        interval = float(getattr(sched, "interval_sec", default_interval) or default_interval)
        return (now_ts - last) >= interval

    sched.can_emit = can_emit
    return True

__all__ = ["apply_guard"]
