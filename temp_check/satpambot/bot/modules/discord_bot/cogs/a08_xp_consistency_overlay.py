
from __future__ import annotations
import asyncio, json, logging
from discord.ext import commands

# === injected helper: KULIAH/MAGANG payload from pinned ===
def __kuliah_payload_from_pinned(__bot):
    try:
        from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
        kv = PinnedJSONKV(__bot)
        m = kv.get_map()
        if hasattr(m, "__await__"):
            # async version: caller must build asynchronously; skip here
            return None
        def _to_int(v, d=0):
            try: return int(v)
            except Exception:
                try: return int(float(v))
                except Exception: return d
        label = str(m.get("xp:stage:label") or "")
        if not (label.startswith("KULIAH-") or label.startswith("MAGANG")):
            return None
        cur = _to_int(m.get("xp:stage:current", 0), 0)
        req = _to_int(m.get("xp:stage:required", 1), 1)
        pct = float(m.get("xp:stage:percent", 0) or 0.0)
        total = _to_int(m.get("xp:bot:senior_total", 0), 0)
        st0 = _to_int(m.get("xp:stage:start_total", max(0, total - cur)), max(0, total - cur))
        status = f"{label} ({pct}%)"
        import json as _json
        status_json = _json.dumps({
            "label": label, "percent": pct, "remaining": max(0, req-cur),
            "senior_total": total,
            "stage": {"start_total": st0, "required": req, "current": cur}
        }, separators=(",",":"))
        return status, status_json
    except Exception:
        return None
# === end helper ===

log = logging.getLogger(__name__)

def _to_int(v, d=0):
    try: return int(v)
    except Exception:
        try: return int(float(v))
        except Exception: return d

class XpConsistencyOverlay(commands.Cog):
    """Consistency guard that ONLY writes learning:status(_json) from pinned KULIAH/MAGANG stage."""
    def __init__(self, bot):
        self.bot = bot
        from satpambot.bot.modules.discord_bot.helpers.confreader import cfg_int
        self.interval = cfg_int("XP_CONSISTENCY_INTERVAL", 300)

    async def _tick(self):
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
            kv = PinnedJSONKV(self.bot)
            us = UpstashClient()

            m = await kv.get_map()
            label = str(m.get("xp:stage:label") or "")
            if not label.startswith(("KULIAH-","MAGANG")):
                # do nothing if pinned not ready
                return
            cur = _to_int(m.get("xp:stage:current", 0), 0)
            req = _to_int(m.get("xp:stage:required", 1), 1)
            pct = float(m.get("xp:stage:percent", 0) or 0.0)
            total = _to_int(m.get("xp:bot:senior_total", 0), 0)
            st0 = _to_int(m.get("xp:stage:start_total", max(0, total - cur)), max(0, total - cur))

            status = f"{label} ({pct}%)"
            status_json = json.dumps({
                "label": label, "percent": pct, "remaining": max(0, req-cur),
                "senior_total": total,
                "stage": {"start_total": st0, "required": req, "current": cur}
            }, separators=(",",":"))

            # Read current
            try:
                cur_status = await us.get_raw("learning:status")
            except Exception:
                cur_status = None
            try:
                cur_json = await us.get_raw("learning:status_json")
            except Exception:
                cur_json = None

            # Only write when needed
            if str(cur_status) != status:
                await us.set("learning:status", (_status if _status is not None else (_status if _status is not None else (_status if _status is not None else status))))
            if str(cur_json) != status_json:
                await us.set("learning:status_json", (_status_json if _status_json is not None else (_status_json if _status_json is not None else (_status_json if _status_json is not None else status_json))))

        except Exception as e:
            log.debug("[xp-consistency] tick failed: %r", e)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        while True:
            await self._tick()
            await asyncio.sleep(self.interval)

async def setup(bot):
    await bot.add_cog(XpConsistencyOverlay(bot))
