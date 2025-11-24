
from __future__ import annotations
import json, logging, asyncio
from urllib.parse import quote
from discord.ext import commands

# === injected helper: pinned-based payload for KULIAH/MAGANG ===
def __kuliah_payload_from_pinned(__bot):
    try:
        from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
        kv = PinnedJSONKV(__bot)
        m = kv.get_map()
        # If async, ignore
        if hasattr(m, "__await__"): 
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

class LearningStatusRepairOnceOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._done = False

    async def _get(self, client, key: str):
        try:
            return await client.get_raw(key)
        except Exception as e:
            log.debug("[learning-repair-once] GET %s fail: %r", key, e); return None

    async def _set(self, client, key: str, value: str):
        try:
            v = quote(str(value), safe="")
            d = await client._apost(f"/set/{key}/{v}")
            return isinstance(d, dict) and "result" in d
        except Exception as e:
            log.debug("[learning-repair-once] SET %s fail: %r", key, e); return False

    async def _repair_once(self):
        if self._done: return
        self._done = True
        try:
            from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
            us = UpstashClient()
            label = await self._get(us, "xp:stage:label")
            cur   = _to_int(await self._get(us, "xp:stage:current"), 0)
            req   = _to_int(await self._get(us, "xp:stage:required"), 1)
            pct   = float(await self._get(us, "xp:stage:percent") or 0.0)
            total = _to_int(await self._get(us, "xp:bot:senior_total"), 0)
            if not (str(label or "").startswith(("KULIAH-","MAGANG"))):
                log.info("[learning-repair-once] skip: stage label not KULIAH/MAGANG (%r)", label); return
            st0 = _to_int(await self._get(us, "xp:stage:start_total"), max(0, total - cur))
            if st0 <= 0: st0 = max(0, total - cur)
            status = f"{label} ({pct}%)"
            payload = {"label": str(label), "percent": pct, "remaining": max(0, req-cur),
                       "senior_total": total,
                       "stage": {"start_total": st0, "required": req, "current": cur}}
            new_json = json.dumps(payload, separators=(",",":"))
            cur_status = await self._get(us, "learning:status")
            cur_json   = await self._get(us, "learning:status_json")
            w = 0
            if str(cur_status) != status:
                if await self._set(us, "learning:status", status): w += 1
            if str(cur_json) != new_json:
                if await self._set(us, "learning:status_json", new_json): w += 1
            if w: log.warning("[learning-repair-once] repaired %d key(s) -> %s", w, status)
            else: log.info("[learning-repair-once] already consistent -> %s", status)
        except Exception as e:
            log.warning("[learning-repair-once] failed: %r", e)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(1.5)
        await self._repair_once()

async def setup(bot):
    await bot.add_cog(LearningStatusRepairOnceOverlay(bot))
