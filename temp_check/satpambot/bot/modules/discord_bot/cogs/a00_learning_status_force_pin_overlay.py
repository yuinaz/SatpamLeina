
from __future__ import annotations
import logging, asyncio, json
from discord.ext import commands

log = logging.getLogger(__name__)

def _to_int(v, d=0):
    try: return int(v)
    except Exception:
        try: return int(float(v))
        except Exception: return d

class LearningStatusForcePinOverlay(commands.Cog):
    """On boot, if learning:status_json label != KULIAH/MAGANG, overwrite from pinned xp:stage:*."""
    def __init__(self, bot):
        self.bot = bot
        self._done = False

    async def _run_once(self):
        if self._done:
            return
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            kv = PinnedJSONKV(self.bot)
            m = await kv.get_map()

            label = str(m.get("xp:stage:label") or "")
            cur   = _to_int(m.get("xp:stage:current", 0), 0)
            req   = _to_int(m.get("xp:stage:required", 1), 1)
            pct   = float(m.get("xp:stage:percent", 0) or 0.0)
            if not label.startswith(("KULIAH-","MAGANG")):
                return

            raw = m.get("learning:status_json")
            try: j = json.loads(raw) if isinstance(raw, str) else (raw or {})
            except Exception: j = {}
            old_label = str((j or {}).get("label") or "")

            if not old_label.startswith(("KULIAH-","MAGANG")):
                status = f"{label} ({pct}%)"
                status_json = json.dumps({
                    "label": label, "percent": pct, "remaining": max(0, req-cur),
                    "senior_total": _to_int(m.get("xp:bot:senior_total", 0), 0),
                    "stage": {"start_total": max(0, _to_int(m.get("xp:bot:senior_total", 0), 0) - cur),
                              "required": req, "current": cur}
                }, separators=(",",":"))
                await kv.set_multi({
                    "learning:status": status,
                    "learning:status_json": status_json,
                })
                log.warning("[learning-force-pin] repaired learning:status(_json) -> %s %s/%s (%.1f%%)", label, cur, req, pct)

            self._done = True
        except Exception as e:
            log.debug("[learning-force-pin] skip: %r", e)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(1.5)
        await self._run_once()

async def setup(bot):
    await bot.add_cog(LearningStatusForcePinOverlay(bot))
