
from __future__ import annotations
import logging, asyncio
from discord.ext import commands

log = logging.getLogger(__name__)

def _to_int(v, d=0):
    try: return int(v)
    except Exception:
        try: return int(float(v))
        except Exception: return d

class XpLadderRuntimeAutorankOverlay(commands.Cog):
    """Autorank that trusts pinned stage (KULIAH/MAGANG). Avoids bogus S1 logs at boot."""
    def __init__(self, bot):
        self.bot = bot
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_int
        self.interval = cfg_int("XP_AUTORANK_INTERVAL", 300)
        self._last = None

    async def _tick(self):
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            kv = PinnedJSONKV(self.bot)
            m = await kv.get_map()

            label = str(m.get("xp:stage:label") or "")
            cur   = _to_int(m.get("xp:stage:current", 0), 0)
            req   = _to_int(m.get("xp:stage:required", 1), 1)
            pct   = float(m.get("xp:stage:percent", 0) or 0.0)

            # Only operate/log when KULIAH/MAGANG + sane numbers
            if not label.startswith(("KULIAH-","MAGANG")) or req <= 0:
                return

            state = (label, cur, req, round(pct,1))
            if state == self._last:
                return
            self._last = state

            # Here you'd adjust roles/ranks; we only log sanitized status
            log.info("[autorank] %s (%.1f%%) xp=%s", label, pct, cur)
        except Exception as e:
            log.debug("[autorank] tick failed: %r", e)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        # Warm-up delay to let bootstrap/repair overlays finish
        await asyncio.sleep(3)
        while True:
            await self._tick()
            await asyncio.sleep(self.interval)

async def setup(bot):
    await bot.add_cog(XpLadderRuntimeAutorankOverlay(bot))
