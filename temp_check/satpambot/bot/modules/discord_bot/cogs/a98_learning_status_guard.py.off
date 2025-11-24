from discord.ext import commands
import os, json
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from ..helpers.rank_utils import is_lower

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
            return j.get("result")
        except Exception:
            return None

    async def pipeline(self, session, commands):
        if not self.enabled or not commands: return False
        import aiohttp
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as sess:
            async with sess.post(f"{self.url}/pipeline", headers=headers, json=commands, timeout=15) as r:
                try:
                    r.raise_for_status()
                    return True
                except Exception:
                    return False

upstash = _Upstash()

class LearningStatusGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.period = max(30, int(os.getenv("LEARNING_GUARD_PERIOD_SEC","60") or "60"))
        self.task = self.loop.start()

    def cog_unload(self):
        try: self.loop.cancel()
        except Exception: pass

    @tasks.loop(seconds=30)
    async def loop(self):
        if not upstash.enabled: return
        now = datetime.now(timezone.utc)
        if int(now.timestamp()) % self.period != 0: return
        try:
            import aiohttp, json

            async with aiohttp.ClientSession() as session:
                raw = await upstash.get(session, "learning:status_json")
                if not raw: return
                try:
                    j = json.loads(raw)
                    live = j.get("label")
                except Exception:
                    return
                max_label = await upstash.get(session, "learning:last_max_label")
                if max_label and isinstance(max_label, str):
                    max_label = max_label.strip('"')
                allow_down = (os.getenv("LEARNING_ALLOW_DOWNGRADE","0").lower() in ("1","true","yes","on","y"))
                if allow_down:
                    # When downgrades are allowed, just track latest live label and skip force-upgrade
                    if (not max_label) or is_lower(max_label, live):
                        await upstash.pipeline(session, [["SET","learning:last_max_label", live]])
                    return
                if not max_label or is_lower(max_label, live):
                    await upstash.pipeline(session, [["SET","learning:last_max_label", live]])
                    return
                if is_lower(live, max_label):
                    phase = (max_label.split("-")[0]) if max_label else "SMP"
                    status = f"{max_label} (100.0%)"
                    status_json = json.dumps({"label":max_label}, separators=(",",":"))
                    await upstash.pipeline(session, [
                        ["SET","learning:status", status],
                        ["SET","learning:status_json", status_json],
                        ["SET","learning:phase", phase],
                    ])
        except Exception:
            pass

    @loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
async def setup(bot: commands.Bot):
    await bot.add_cog(LearningStatusGuard(bot))

def _calc_kuliah(total:int):
    try:
        from ..helpers.xp_total_resolver import stage_from_total
        label, pct, meta = stage_from_total(int(total))
        rem = int(max(0, meta.get('required',1) - meta.get('current',0)))
        return label, pct, rem
    except Exception:
        # Fallback simple buckets
        th=[0,19000,35000,58000,70000,96500,158000,220000,262500]
        nm=['S1','S2','S3','S4','S5','S6','S7','S8']
        i=max([j for j in range(0,8) if total>=th[j]] or [0])
        cur=th[i]; nxt=th[i+1] if i+1<len(th) else cur
        pct=100.0 if nxt<=cur else round(((total-cur)/(nxt-cur))*100.0,1)
        rem=0 if total>=nxt else (nxt-total)
        return f'KULIAH-{nm[i]}', pct, rem

async def _guard_set(status: str, status_json: str, session):
    import json as _j
    from satpambot.bot.modules.discord_bot.helpers.upstash import UpstashClient as _U
    upstash=_U()
    try:
        j=_j.loads(status_json) if status_json else {}
    except Exception:
        j={}
    tot=int(j.get("senior_total") or j.get("senior_total_xp") or 0)
    lbl, pct, rem = _calc_kuliah(tot)
    desired_status = f"{lbl} ({pct}%)"
    desired_json   = _j.dumps({"label": lbl, "percent": pct, "remaining": rem, "senior_total": tot}, separators=(",",":"))
    if (status or "").strip()!=desired_status or (status_json or "").strip()!=desired_json:
        status, status_json = desired_status, desired_json
    await upstash.pipeline(session, [
        ["SET","learning:status", status],
        ["SET","learning:status_json", status_json]
    ])
