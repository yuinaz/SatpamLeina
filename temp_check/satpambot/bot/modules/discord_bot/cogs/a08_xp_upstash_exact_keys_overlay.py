
from __future__ import annotations
import os, logging, inspect, asyncio
from typing import Any, Optional
from discord.ext import commands

# Import cmd helper (sync in your tree). Do NOT import non-existent symbols.
from ..helpers.upstash_rest import cmd as upstash_cmd

log = logging.getLogger(__name__)

def _extract_uid(x: Any) -> Optional[int]:
    try:
        # int already
        if isinstance(x, int):
            return int(x)
        # discord Member/User with .id
        uid = getattr(x, "id", None)
        if uid is not None:
            return int(uid)
        # string of digits
        if isinstance(x, str) and x.isdigit():
            return int(x)
    except Exception:
        pass
    return None

def _norm(args: tuple, kwargs: dict) -> tuple[Optional[int], Optional[int], Optional[str]]:
    uid: Optional[int] = None
    amount: Optional[int] = None
    reason: Optional[str] = None

    if args:
        # accept Member/User or raw int for uid
        uid = _extract_uid(args[0])
        if len(args) >= 2:
            try:
                amount = int(args[1])
            except Exception:
                amount = None
        if len(args) >= 3:
            reason = args[2]

    if uid is None:
        uid = _extract_uid(kwargs.get("user_id") or kwargs.get("uid"))
    if amount is None:
        a = kwargs.get("amount", kwargs.get("delta"))
        try:
            amount = int(a) if a is not None else None
        except Exception:
            amount = None
    if reason is None:
        reason = kwargs.get("reason")

    return uid, amount, reason

def _maybe_schedule(x: Any):
    try:
        if inspect.isawaitable(x):
            asyncio.get_running_loop().create_task(x)
    except Exception:
        pass

class XpUpstashSinkOverlay(commands.Cog):
    """Exact-key Upstash sink; robust to mixed event shapes and sync/async helper."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.prefix = os.getenv("XP_EXACT_KEY_PREFIX", "xp:u:")

    @commands.Cog.listener()
    async def on_satpam_xp(self, *args: Any, **kwargs: Any):
        uid, amount, reason = _norm(args, kwargs)
        if uid is None or amount is None:
            log.warning("[xp-upstash-sink] drop malformed satpam_xp: args=%s kwargs=%s", args, kwargs)
            return

        try:
            _maybe_schedule(upstash_cmd("INCRBY", f"{self.prefix}{uid}", str(int(amount))))
            if reason:
                _maybe_schedule(upstash_cmd("HINCRBY", "xp:bucket:reasons", str(reason), str(int(amount))))
        except Exception as e:
            log.warning("[xp-upstash-sink] upstash write failed: %s", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(XpUpstashSinkOverlay(bot))
