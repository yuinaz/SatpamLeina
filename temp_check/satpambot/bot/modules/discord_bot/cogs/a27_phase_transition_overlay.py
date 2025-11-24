import os, json, asyncio, time
from typing import Optional
import discord
from discord.ext import commands, tasks
import os

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

def _env_true(name: str) -> bool:
    v = os.getenv(name, '')
    return str(v).strip() not in ('', '0', 'false', 'False', 'no', 'None')

class _Upstash:
    def __init__(self):
        self.base = os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN","")
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else None
        self.enabled = bool(self.base and self.token)

    async def get_json(self, key: str) -> Optional[dict]:
        if not self.enabled: return None
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as cx:
                r = await cx.get(f"{self.base}/get/{key}", headers=self.headers)
                res = r.json().get("result")
                if isinstance(res, str):
                    try: return json.loads(res)
                    except Exception: return None
                return res if isinstance(res, dict) else None
        except Exception:
            return None

    async def set(self, key: str, val: str):
        if not self.enabled: return None
        import httpx, urllib.parse
        payload = urllib.parse.quote(val, safe="")
        async with httpx.AsyncClient(timeout=10) as cx:
            try:
                await cx.post(f"{self.base}/set/{key}/{payload}", headers=self.headers)
            except Exception:
                pass

class PhaseTransition(commands.Cog):
    """Monitor fase belajar. Ketika MAGANG selesai -> aktifkan WORK (notifikasi owner).
    Anti-spam via key upstash 'phase:work:activated'.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enable = os.getenv("PHASE_TRANSITION_ENABLE","1") == "1"
        self.owner_id = int(os.getenv("BOT_OWNER_ID","0"))
        self.notify_channel_id = int(os.getenv("GATE_NOTIFY_CHANNEL_ID", os.getenv("QNA_CHANNEL_ID","1426571542627614772")))
        self.status_json_key = os.getenv("LEARNING_STATUS_JSON_KEY","learning:status_json")
        self._up = _Upstash()
        self._started = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.enable or self._started:
            return
        self._started = True
        self.loop.start()

    @tasks.loop(minutes=5)
    async def loop(self):
        js = await self._up.get_json(self.status_json_key)
        if not js: return
        label = str(js.get("label",""))
        percent = float(js.get("percent", 0.0))
        if label.startswith("MAGANG-") and percent >= 100.0:
            # check guard key
            guard_key = "phase:work:activated"
            existing = await self._up.get_json(guard_key)
            if existing:
                return
            # set guard
            await self._up.set(guard_key, json.dumps({"ts": int(time.time())}))

            # notify owner & channel
            try:
                if self.owner_id:
                    user = await self.bot.fetch_user(self.owner_id)
                    if user:
                        await user.send("✅ Leina selesai MAGANG dan telah masuk fase **KERJA**. Silakan buka **GATE STATUS** untuk belajar + bekerja pra-Governor.")
            except Exception:
                pass
            try:
                ch = self.bot.get_channel(self.notify_channel_id)
                if ch:
                    await ch.send("📣 Transition: Leina memasuki fase **KERJA**. Mohon *owner* membuka **Gate Status** (belajar + bekerja), tanpa spam.")
            except Exception:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(PhaseTransition(bot))
