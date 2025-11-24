
"""
a99_focus_log_router_final.py — SAFE WRAPPER HOTFIX
---------------------------------------------------
Goal: stop infinite routing loops across patched Messageable.send() wrappers
observed as "maximum recursion depth exceeded" and giant call chains through
rate_limit_guard -> public_send_router -> shadow_public_silencer -> dm_muzzle -> a99 -> ...

Strategy: install a *final* lightweight wrapper that:
  - Delegates to the previously installed chain for normal sends
  - Adds a small re-entrancy guard; on re-entry it directly calls the raw
    library send (discord.abc.Messageable.send), which breaks the loop.

This preserves most earlier behaviors (rate limit, muzzle, etc.) for first-hop
sends, but prevents a99 from re-triggering the entire chain when a send is
routed to another destination.
"""
import logging
import contextvars
from discord.abc import Messageable as _Messageable

log = logging.getLogger(__name__)

# The raw library send (unpatched baseline)
_LIB_SEND = _Messageable.send

# A tiny guard to detect "we are already inside a patched send" so we can bail out to raw
_GUARD = contextvars.ContextVar("a99_router_guard", default=False)

def _install_safe_wrapper():
    # Whatever chain is currently installed before we (a99) patch in.
    prev_send = _Messageable.send

    async def _safe_wrapper(self, *args, **kwargs):
        # If we re-enter (because another router calls .send() again),
        # short-circuit to the raw library send to break the loop.
        if _GUARD.get():
            return await _LIB_SEND(self, *args, **kwargs)
        token = _GUARD.set(True)
        try:
            # Normal path: keep earlier behaviors intact.
            return await prev_send(self, *args, **kwargs)
        finally:
            _GUARD.reset(token)

    _Messageable.send = _safe_wrapper
    log.info("[a99_focus_log_router_final] safe wrapper installed (loop-guard + raw-send on re-entry)")

def setup(bot):
    _install_safe_wrapper()
