from __future__ import annotations
import logging
from typing import Any, Union
from discord import Member
from discord.ext import commands
log = logging.getLogger(__name__)

def _to_uid(u: Union[int,str,Member,Any]) -> int:
    try:
        if isinstance(u, Member): return int(u.id)
        if isinstance(u, (int,)): return int(u)
        if hasattr(u, "id"): return int(getattr(u, "id"))
        return int(str(u))
    except Exception:
        return 0

def _to_int(x, d=0):
    try: return int(x)
    except Exception:
        try: return int(float(x))
        except Exception: return d

class PassiveToBotBridgeOverlay(commands.Cog):
    def __init__(self, bot): self.bot=bot
    async def _apply(self, uid: int, amt: int, reason: str):
        pass
    @commands.Cog.listener()
    async def on_xp_add(self, *args: Any, **kwargs: Any):
        
        # tolerant signature adapter (accepts 3..5 args)
        uid = kwargs.get("uid") or kwargs.get("user_id")
        amt = kwargs.get("amt") or kwargs.get("amount")
        reason = kwargs.get("reason")
        ints = [a for a in args if isinstance(a, int)]
        strs = [a for a in args if isinstance(a, str)]
        if uid is None and ints:
            uid = ints[0]
        if amt is None and len(ints) >= 2:
            amt = ints[1]
        if reason is None and strs:
            reason = strs[0]
        if uid is None or amt is None:
            return
        try:
            await self._apply(_to_uid(uid), _to_int(amt,0), reason)
        except Exception as e:
            log.warning("[passive-to-bot] fail: %r", e)
    @commands.Cog.listener()
    async def on_satpam_xp(self, *args, **kwargs):
        try:
            await self.on_xp_add(*args, **kwargs)
        except Exception as e:
            log.warning("[passive-to-bot] on_satpam_xp fail: %r", e)

async def setup(bot):
    try:
        for name, cog in list(bot.cogs.items()):
            if cog.__class__.__name__ in {"PassiveShadowGlobalXPOverlay","PassiveToBotBridgeOverlay"}:
                bot.remove_cog(name)
    except Exception:
        pass
    await bot.add_cog(PassiveToBotBridgeOverlay(bot))
