
from __future__ import annotations
import asyncio, json, logging
from discord.ext import commands

log = logging.getLogger(__name__)

def _to_int(v, d=0):
    try: return int(v)
    except Exception:
        try: return int(float(v))
        except Exception: return d

class LearningStatusUpstashEnforcerOverlay(commands.Cog):
    """
    Keeps `learning:status` and `learning:status_json` consistent with *pinned* xp:stage
    (only when label starts with KULIAH-/MAGANG). If any writer sets SMP-L*, we rewrite it back.
    - Immediate fix at boot, then periodic (configurable).
    - No spam: only writes when value actually differs.
    """
    def __init__(self, bot):
        self.bot = bot
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_int
        self.interval = int(cfg_int("LEARNING_STATUS_ENFORCER_INTERVAL_SEC", 300))
        self._task = None

    async def _once(self):
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
            kv = PinnedJSONKV(self.bot)
            us = UpstashClient()

            m = await kv.get_map()
            label = str(m.get("xp:stage:label") or "")
            if not label.startswith(("KULIAH-","MAGANG")):
                return

            cur = _to_int(m.get("xp:stage:current", 0), 0)
            req = _to_int(m.get("xp:stage:required", 1), 1)
            pct = float(m.get("xp:stage:percent", 0) or 0.0)
            total = _to_int(m.get("xp:bot:senior_total", 0), 0)

            status = f"{label} ({pct}%)"
            status_json = json.dumps({
                "label": label, "percent": pct, "remaining": max(0, req-cur),
                "senior_total": total,
                "stage": {"start_total": max(0, total - cur), "required": req, "current": cur}
            }, separators=(",",":"))

            # Read current Upstash values
            try:
                cur_status = await us.get_raw("learning:status")
            except Exception:
                cur_status = None
            try:
                cur_status_json = await us.get_raw("learning:status_json")
            except Exception:
                cur_status_json = None

            writes = {}
            if str(cur_status) != status:
                writes["learning:status"] = status
            if str(cur_status_json) != status_json:
                writes["learning:status_json"] = status_json

            if writes:
                # Write to Upstash and pinned KV (for consistency)
                for k, v in writes.items():
                    try:
                        await us.set(k, v)
                    except Exception as e:
                        log.warning("[learning-enforcer] upstash set %s failed: %r", k, e)
                await kv.set_multi(writes)
                log.warning("[learning-enforcer] repaired: %s", ", ".join(writes.keys()))
        except Exception as e:
            log.debug("[learning-enforcer] once failed: %r", e)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        # quick immediate repair
        await self._once()
        # periodic guard
        while True:
            await asyncio.sleep(self.interval)
            await self._once()

async def setup(bot):
    await bot.add_cog(LearningStatusUpstashEnforcerOverlay(bot))
