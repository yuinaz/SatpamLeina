from __future__ import annotations

# modules/discord_bot/utils/mod_guard.py
import time
from typing import Dict, Tuple, Optional

# Simple TTL claim so one message is only acted upon once across cogs
CLAIMS: Dict[int, Tuple[str, float]] = {}
DEFAULT_TTL = 90.0  # seconds

def _vacuum(now: float) -> None:
    expired = [mid for mid, (_, ts) in CLAIMS.items() if ts <= now]
    for mid in expired:
        CLAIMS.pop(mid, None)

def claim(message_id: int, actor: str, ttl: float = DEFAULT_TTL) -> bool:
    now = time.monotonic()
    _vacuum(now)
    if message_id in CLAIMS:
        return False
    CLAIMS[message_id] = (actor, now + ttl)
    return True

def who_claimed(message_id: int) -> Optional[str]:
    now = time.monotonic()
    _vacuum(now)
    item = CLAIMS.get(message_id)
    return item[0] if item else None
