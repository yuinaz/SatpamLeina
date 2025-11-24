from __future__ import annotations
import logging, asyncio
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

class PassiveShadowGlobalXPOverlay(commands.Cog):
    def __init__(self, bot): self.bot=bot
    async def _apply(self, uid: int, amt: int, reason: str):
        pass
    @commands.Cog.listener()
    async def on_xp_add(self, uid, amt, reason:str):
        try:
            await self._apply(_to_uid(uid), _to_int(amt,0), reason)
        except Exception as e:
            log.warning("[passive-shadow-global] fail: %r", e)
    @commands.Cog.listener()
    async def on_satpam_xp(self, *a, **kw):
        try:
            await self.on_xp_add(*a, **kw)
        except Exception as e:
            log.warning("[passive-shadow-global] on_satpam_xp fail: %r", e)

async def setup(bot):
    try:
        for name, cog in list(bot.cogs.items()):
            if cog.__class__.__name__ in {"PassiveShadowGlobalXPOverlay","PassiveToBotBridgeOverlay"}:
                bot.remove_cog(name)
    except Exception:
        pass
    await bot.add_cog(PassiveShadowGlobalXPOverlay(bot))
