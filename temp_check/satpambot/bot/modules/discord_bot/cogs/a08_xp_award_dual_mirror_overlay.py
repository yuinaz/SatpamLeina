import logging, os, asyncio, json
from discord.ext import commands
from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
from satpambot.bot.modules.discord_bot.helpers.stage_tracker import StageTracker
from satpambot.bot.modules.discord_bot.helpers.xp_total_resolver import stage_from_total

log = logging.getLogger(__name__)

def _int(v, d=0):
    try:
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return d

class XPAwardDualMirror(commands.Cog):
    """Mirror XP awards into a pinned JSON KV (staging, reset per level)."""
    def __init__(self, bot):
        self.bot = bot
        self.kv = PinnedJSONKV(bot)
        self._busy = False
        self.total_key = os.getenv("XP_SENIOR_KEY","xp:bot:senior_total")
        self.tracker = StageTracker(self.kv, total_key=self.total_key)

    def _extract(self, *args, **kwargs):
        delta = kwargs.get("amount") or kwargs.get("delta") or kwargs.get("xp") or 0
        return _int(delta, 0)

    async def _apply(self, delta: int):
        if not delta:
            return
        try:
            # 1) Update global total (fallback to KV if resolver fails)
            try:
                from satpambot.bot.modules.discord_bot.helpers.xp_total_resolver import resolve_senior_total
                cur_total = await resolve_senior_total() or 0
            except Exception:
                m0 = await self.kv.get_map()
                cur_total = _int(m0.get(self.total_key, 0), 0)
            new_total = int(cur_total) + int(delta)

            # 2) Apply staging updates (resets per level)
            m = await self.tracker.add(int(delta))
            label   = str(m.get("xp:stage:label"))
            percent = float(m.get("xp:stage:percent", 0) or 0)
            req     = _int(m.get("xp:stage:required", 1), 1)
            cur     = _int(m.get("xp:stage:current", 0), 0)

            # 3) Compose status_json strictly from staging
            status_json = {"label":label,"percent":percent,"remaining":max(0, req-cur),
                           "senior_total":new_total,"stage":{"start_total": new_total - cur, "required": req, "current": cur}}

            updates = {
                self.total_key: new_total,
                "learning:status": f"{label} ({percent}%)",
                "learning:status_json": status_json,
            }
            await self.kv.set_multi(updates)
            log.info("[xp-dual] staged delta=%s new_total=%s cur=%s/%s (%s)", delta, new_total, cur, req, label)
        except Exception as e:
            log.warning("[xp-dual] mirror failed: %r", e)

    async def on_event_common(self, *args, **kwargs):
        if self._busy:
            return
        self._busy = True
        try:
            await self._apply(self._extract(*args, **kwargs))
        finally:
            self._busy = False

    @commands.Cog.listener()
    async def on_xp_add(self, *args, **kwargs):
        await self.on_event_common(*args, **kwargs)

    @commands.Cog.listener()
    async def on_xp_award(self, *args, **kwargs):
        await self.on_event_common(*args, **kwargs)

    @commands.Cog.listener("on_satpam_xp")
    async def on_satpam_xp(self, *args, **kwargs):
        await self.on_event_common(*args, **kwargs)

async def setup(bot: commands.Bot):
    await bot.add_cog(XPAwardDualMirror(bot))
