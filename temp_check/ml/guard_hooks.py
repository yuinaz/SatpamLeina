"""Minimal guard hooks for health-checks.

This file intentionally tiny; provides get_health() for watchdogs.
No side effects; safe to keep even if a fuller implementation exists later.
"""

def get_health():
    try:
        import time
        ts = int(time.time())
    except Exception:
        ts = 0
    return {"status": "ok", "ts": ts, "details": {"source": "ml.guard_hooks:stub"}}
