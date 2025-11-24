from __future__ import annotations
import logging
from typing import Any, Optional
from discord.ext import commands
log = logging.getLogger(__name__)

_ALLOWED_GLOBAL_PREFIX = ("chat:", "passive_", "force-include", "system:")

def _to_int(v, d=None):
    try:
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return d

class XPEventBridgeOverlay(commands.Cog):
    def __init__(self, bot): self.bot = bot

    async def _ensure_integer_key(self):
        from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
        cli = UpstashClient()
        cur = await cli.get_raw("xp:bot:senior_total")
        n = _to_int(cur, None)
        if n is None:
            try:
                from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
                pin = PinnedJSONKV(self.bot).get_map()
                n = _to_int(pin.get("xp:bot:senior_total"), 0)
            except Exception:
                n = 0
            await cli._apost(f"/set/xp:bot:senior_total/{n}")
            log.warning("[xp-bridge] normalized senior_total -> %d", n)

    async def _incrby(self, delta: int):
        from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
        cli = UpstashClient()
        try:
            await self._ensure_integer_key()
            newv = await cli._apost(f"/incrby/xp:bot:senior_total/{int(delta)}")
            log.info("[xp-bridge] INCR -> %s (+%s)", str(newv).strip(), delta)
        except Exception as e:
            log.warning("[xp-bridge] INCRBY fail: %r; fallback to set", e)
            cur = await cli.get_raw("xp:bot:senior_total")
            n = _to_int(cur, 0)
            newv = n + int(delta)
            await cli._apost(f"/set/xp:bot:senior_total/{newv}")
            log.info("[xp-bridge] SET -> %s (+%s)", newv, delta)

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
        d = _to_int(amt, 0)
        if not d: return
        rs = (reason or "").strip().lower()
        if rs.startswith("qna"):
            log.debug("[xp-bridge] ignore qna reason: %s", rs)
            return
        if not any(rs.startswith(p) for p in _ALLOWED_GLOBAL_PREFIX):
            log.debug("[xp-bridge] ignore non-global reason: %s", rs)
            return
        await self._incrby(d)

async def setup(bot):
    try:
        for name, cog in list(bot.cogs.items()):
            if isinstance(cog, XPEventBridgeOverlay) or cog.__class__.__name__ == "XPEventBridgeOverlay":
                bot.remove_cog(name)
    except Exception:
        pass
    await bot.add_cog(XPEventBridgeOverlay(bot))
