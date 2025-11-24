from discord.ext import commands
import os, json, logging
from datetime import datetime, timezone

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

import discord
from discord.ext import commands, tasks

from ..helpers.ladder_loader import load_ladders, compute_senior_label
from ..helpers.rank_utils import is_lower

log = logging.getLogger(__name__)

class _Upstash:
    def __init__(self):
        self.url = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
        self.enabled = bool(self.url and self.token and os.getenv("KV_BACKEND","").lower()=="upstash_rest")

    async def _get_json(self, session, path: str):
        import aiohttp
        headers = {"Authorization": f"Bearer {self.token}"}
        async with session.get(f"{self.url}{path}", headers=headers, timeout=15) as r:
            r.raise_for_status()
            return await r.json()

    async def get(self, session, key: str):
        if not self.enabled: return None
        try:
            j = await self._get_json(session, f"/get/{key}")
            v = j.get("result")
            return None if v is None else str(v)
        except Exception:
            return None

    async def pipeline(self, session, commands):
        if not self.enabled or not commands: return False
        import aiohttp
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as sess:
            async with sess.post(f"{self.url}/pipeline", headers=headers, json=commands, timeout=15) as r:
                if r.status // 100 != 2:
                    return False
                try:
                    await r.json()
                except Exception:
                    pass
                return True

upstash = _Upstash()

def _safe_int(raw: str) -> int:
    if raw is None: return 0
    try: return int(raw)
    except Exception:
        try:
            j = json.loads(raw); 
            return int(j.get("overall",0))
        except Exception:
            return 0

class A00LearningStatusRefreshOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.period = max(60, int(os.getenv("LEARNING_REFRESH_PERIOD_SEC", "300") or "300"))
        self.xp_key = os.getenv("XP_SENIOR_KEY", "xp:bot:senior_total")
        self.ladders = load_ladders(__file__)
        self.task = self.loop.start()

    def cog_unload(self):
        try: self.loop.cancel()
        except Exception: pass

    async def _compute(self, session):
        raw_total = await upstash.get(session, self.xp_key)
        total = _safe_int(raw_total)
        label, pct, rem = compute_senior_label(total, self.ladders or {})
        live_raw = await upstash.get(session, "learning:status_json")
        live_label = None
        if live_raw:
            try: live_label = json.loads(live_raw).get("label")
            except Exception: live_label = None
        floor = os.getenv("LEARNING_MIN_LABEL","").strip() or live_label
        if floor and is_lower(label, floor):
            label = floor
        phase = (label.split("-")[0]) if label else "SMP"
        status = f"{label} ({pct:.1f}%)"
        status_json = json.dumps({"label":label,"percent":pct,"remaining":rem,"senior_total":total}, separators=(",",":"))
        return {"status":status, "status_json":status_json, "phase":phase, "label":label}

    @tasks.loop(seconds=30)
    async def loop(self):
        if os.getenv("DISABLE_LEARNING_REFRESH"): return
        if not upstash.enabled: return
        now = datetime.now(timezone.utc)
        if int(now.timestamp()) % self.period != 0: return
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                data = await self._compute(session)
                live_raw = await upstash.get(session, "learning:status_json")
                if live_raw:
                    try:
                        live_label = json.loads(live_raw).get("label")
                        if live_label and is_lower(data["label"], live_label):
                            return
                    except Exception:
                        pass
                await upstash.pipeline(session, [
                    # Guard writes to avoid conflicting with KuliahStageResetOverlay
                    # Enable via LEARNING_STATUS_REFRESH_WRITE=true
                    *([["PING","noop"]]
                      if os.getenv("LEARNING_STATUS_REFRESH_WRITE","").lower() in ("1","true","yes") else []),
                    ["SET", "learning:phase", data["phase"]],
                ])
        except Exception as e:
            log.debug("[a00] refresh skipped: %s", e)

    @loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
async def setup(bot: commands.Bot):
    await bot.add_cog(A00LearningStatusRefreshOverlay(bot))