
from __future__ import annotations
import os, logging
from typing import Optional, Any
from discord.ext import commands

log = logging.getLogger(__name__)

def _parse_int(s: Optional[str], default: int) -> int:
    try:
        return int(s) if s is not None and str(s).strip() != "" else default
    except Exception:
        return default

_TARGET = _parse_int(os.getenv("XP_NORMALIZER_TARGET_PER_MESSAGE", "15"), 15)
_ADJUST_REASONS = {"chat:message", "force-include"}  # sumber yang biasanya +5
_GUARD_PREFIX = "normalize:"

class XpDeltaNormalizerOverlay(commands.Cog):
    """
    Menyetarakan event XP dari berbagai sumber agar konsisten.
    Jika event datang dengan amount 5 dari sumber umum ('chat:message', 'force-include'),
    overlay menambah XP pembeda (dispatch xp_add) supaya total = target (default 15).
    Hindari loop dengan menandai reason prefix 'normalize:'.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        log.info("[xp-normalizer] target per-message = %s", _TARGET)

    def _maybe_adjust(self, uid: int, amount: int, reason: Optional[str]):
        if reason and reason.startswith(_GUARD_PREFIX):
            return
        if amount is None:
            return
        if amount >= _TARGET:
            return
        if reason not in _ADJUST_REASONS and reason is not None:
            return
        delta = _TARGET - int(amount)
        if delta <= 0:
            return
        try:
            # kirim penyesuaian; pendengar sink lain akan menangani sama seperti xp_add biasa
            self.bot.dispatch("xp_add", uid, int(delta), f"{_GUARD_PREFIX}{reason or 'unknown'}")
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_xp_add(self, uid: int, amount: int, reason: Optional[str]=None, *args: Any, **kwargs: Any):
        self._maybe_adjust(uid, amount, reason)

    @commands.Cog.listener()
    async def on_satpam_xp(self, uid: int=None, amount: int=None, reason: Optional[str]=None, *args: Any, **kwargs: Any):
        # toleransi kwargs
        if uid is None: uid = kwargs.get("user_id") or kwargs.get("uid")
        if amount is None: amount = kwargs.get("amount", kwargs.get("delta"))
        try:
            if uid is not None: uid = int(uid)
            if amount is not None: amount = int(amount)
        except Exception:
            return
        if uid is None or amount is None:
            return
        self._maybe_adjust(uid, amount, reason)

    @commands.Cog.listener()
    async def on_xp_award(self, uid: int, amount: int, reason: Optional[str]=None, *args: Any, **kwargs: Any):
        self._maybe_adjust(uid, amount, reason)

async def setup(bot: commands.Bot):
    await bot.add_cog(XpDeltaNormalizerOverlay(bot))
