from __future__ import annotations
import logging, asyncio, re
from discord.ext import commands

log = logging.getLogger(__name__)

def _is_int_str(s):
    return isinstance(s, (str, bytes)) and re.fullmatch(r"-?\d+", s.decode() if isinstance(s, bytes) else s) is not None

def _to_int(v, d=0):
    try:
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return d

class XpLadderReporterOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_str, cfg_int
        self.total_key = cfg_str("XP_SENIOR_KEY","xp:bot:senior_total")
        self.interval = cfg_int("XP_LADDER_REPORT_INTERVAL", 300)
        self._last = None

    async def _tick(self):
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
            kv = PinnedJSONKV(self.bot)
            us = UpstashClient()

            m = await kv.get_map()
            label = str(m.get("xp:stage:label") or "")
            cur   = _to_int(m.get("xp:stage:current",0),0)
            req   = _to_int(m.get("xp:stage:required",1),1)
            pct   = float(m.get("xp:stage:percent",0) or 0.0)

            try:
                total_raw = await us.get_raw(self.total_key)
            except Exception:
                total_raw = None
            total = _to_int(total_raw, _to_int(m.get(self.total_key, 0), 0))

            if label.startswith(("KULIAH-","MAGANG")):
                state = (label, cur, req, round(pct,1), total)
                if state != self._last:
                    self._last = state
                    log.info("[xp-ladder] %s  %4.1f%%  (%s/%s)  total=%s", label, pct, cur, req, total)
            else:
                if total != _to_int((self._last or (None, None, None, None, None))[4], 0):
                    self._last = (None,None,None,None,total)
                    log.info("[xp-ladder] total=%s (pinned stage not ready)", total)
        except Exception as e:
            log.debug("[xp-ladder] tick failed: %r", e)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        while True:
            await self._tick()
            await asyncio.sleep(self.interval)

async def setup(bot):
    await bot.add_cog(XpLadderReporterOverlay(bot))
