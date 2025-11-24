
from __future__ import annotations
import logging, asyncio, os
from typing import Optional

log = logging.getLogger(__name__)

def _intenv(k, d):
    try: return int(os.getenv(k, str(d)))
    except Exception: return d

# monkey-patch xp_event_bridge_overlay to be more lenient and avoid log storms
try:
    from satpambot.bot.modules.discord_bot.cogs import a08_xp_event_bridge_overlay as _xb
    from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
except Exception as e:
    _xb = None
    UpstashClient = None

if _xb is not None and getattr(_xb, "_wrapped_safe_add", False) is False and hasattr(_xb, "get_xp_key"):
    _orig_get_xp_key = _xb.get_xp_key

    def get_xp_key():
        # Force to xp:bot:senior_total unless overridden
        k = os.getenv("XP_TOTAL_KEY", "") or "xp:bot:senior_total"
        return k

    _xb.get_xp_key = get_xp_key

    _orig_xp_add = getattr(_xb, "xp_add", None)
    _limiter = {"last_warn": 0}
    _warn_every = _intenv("XP_BRIDGE_WARN_COOLDOWN_SEC", 600)

    async def xp_add(amount: int = 0):
        """Safe xp_add with type coerce and Upstash fallback client."""
        try:
            amt = int(amount or 0)
        except Exception:
            amt = 0
        if amt <= 0:
            # do nothing on zero/nonpositive
            return False
        key = get_xp_key()
        client = None
        ok = False
        try:
            if UpstashClient is not None:
                client = UpstashClient()
                # Optional preflight: touch get_raw to coerce side-effects/fallback merge
                _ = await client.get_raw(key)
                ok = await client.incrby(key, amt)
        except Exception as e:
            ok = False
        if not ok:
            # one-line warning with cooldown — DO NOT spam
            import time
            now = time.time()
            if now - _limiter["last_warn"] > _warn_every:
                _limiter["last_warn"] = now
                log.warning("[xp-bridge:safe] incr failed; queued via fallback or ignored (amt=%s, key=%s)", amt, key)
        return ok

    _xb.xp_add = xp_add
    _xb._wrapped_safe_add = True
    log.info("[xp-bridge:safe] wrapper active")

async def setup(bot):
    return
