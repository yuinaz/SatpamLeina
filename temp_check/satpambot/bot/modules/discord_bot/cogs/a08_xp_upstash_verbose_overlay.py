from discord.ext import commands

"""
a08_xp_upstash_verbose_overlay.py
Menulis XP ke Upstash secara rinci tanpa mengubah key lama:
- Per-user total   → INCRBY "xp:u:<uid>"
- Bucket senior    → HINCRBY "xp:bucket:senior:users" <uid> <delta>
- Per alasan       → HINCRBY "xp:bucket:reasons" <reason> <delta>
- (Opsional) event → LPUSH "xp:events" {"uid":..,"delta":..,"reason":..,"ts":..}

ENV:
  UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN
  XP_UPSTASH_VERBOSE=1
  XP_UPSTASH_EVENTS_ENABLE=0
  XP_UPSTASH_EVENTS_MAX=1000
  XP_UPSTASH_EVENT_SAMPLE=10
"""
import os, json, time, logging, asyncio
from typing import Tuple

log = logging.getLogger(__name__)

def _env_bool(k, d):
    v = os.getenv(k)
    if v is None: return d
    return str(v).strip().lower() not in ("0","false","no")

VERBOSE = _env_bool("XP_UPSTASH_VERBOSE", True)
EVENTS_ENABLE = _env_bool("XP_UPSTASH_EVENTS_ENABLE", False)
EVENTS_MAX = int(os.getenv("XP_UPSTASH_EVENTS_MAX","1000") or 1000)
EVENT_SAMPLE = max(1, int(os.getenv("XP_UPSTASH_EVENT_SAMPLE","10") or 10))

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN","")

class _Upstash:
    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token
    async def pipeline(self, commands):
        import httpx
        if not self.url or not self.token:
            return None
        try:
            async with httpx.AsyncClient(timeout=8.0) as cli:
                r = await cli.post(f"{self.url}/pipeline", json=commands, headers={
                    "Authorization": f"Bearer {self.token}"
                })
                r.raise_for_status()
                return r.json()
        except Exception as e:
            log.debug("[xp-verbose] pipeline failed: %r", e)
            return None

class XpUpstashVerbose(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = _Upstash(UPSTASH_URL, UPSTASH_TOKEN)
        if not (UPSTASH_URL and UPSTASH_TOKEN):
            log.warning("[xp-verbose] Upstash url/token missing; verbose off.")
        else:
            log.info("[xp-verbose] enabled")

    def _norm(self, *args, **kwargs) -> Tuple[int,int,str]:
        uid = None
        delta = None
        reason = kwargs.get("reason") or kwargs.get("label") or kwargs.get("why") or ""
        if len(args) >= 2:
            uid, delta = args[0], args[1]
        elif len(args) == 1:
            a0 = args[0]
            uid = getattr(a0, "id", None) or a0
            delta = kwargs.get("amount") or kwargs.get("delta") or 0
        else:
            uid = kwargs.get("user_id") or kwargs.get("uid") or kwargs.get("user")
            delta = kwargs.get("amount") or kwargs.get("delta") or 0
        uid = getattr(uid, "id", uid)
        try: uid = int(uid)
        except Exception: uid = 0
        try: delta = int(delta)
        except Exception: delta = 0
        reason = str(reason or "")
        if len(reason) > 40: reason = reason[:37] + "..."
        return uid, delta, reason

    async def _write_verbose(self, uid: int, delta: int, reason: str):
        if not VERBOSE or not uid or not delta:
            return
        cmds = []
        cmds.append(["INCRBY", f"xp:u:{uid}", str(delta)])
        cmds.append(["HINCRBY", "xp:bucket:senior:users", str(uid), str(delta)])
        if reason:
            cmds.append(["HINCRBY", "xp:bucket:reasons", reason, str(delta)])
        if EVENTS_ENABLE:
            ts = int(time.time()*1000)
            if (ts // EVENT_SAMPLE) % EVENT_SAMPLE == 0:
                ev = json.dumps({"uid":uid,"delta":delta,"reason":reason,"ts":ts}, separators=(",",":"))
                cmds.append(["LPUSH", "xp:events", ev])
                cmds.append(["LTRIM", "xp:events", "0", str(EVENTS_MAX-1)])
        await self.db.pipeline(cmds)

    @commands.Cog.listener("on_satpam_xp")
    async def on_satpam_xp(self, *args, **kwargs):
        uid, delta, reason = self._norm(*args, **kwargs)
        await self._write_verbose(uid, delta, reason or "satpam_xp")

    @commands.Cog.listener("on_xp_add")
    async def on_xp_add(self, *args, **kwargs):
        uid, delta, reason = self._norm(*args, **kwargs)
        await self._write_verbose(uid, delta, reason or "xp_add")

    @commands.Cog.listener("on_xp_award")
    async def on_xp_award(self, *args, **kwargs):
        uid, delta, reason = self._norm(*args, **kwargs)
        await self._write_verbose(uid, delta, reason or "xp_award")

    @commands.Cog.listener("xp_add")
    async def xp_add(self, *args, **kwargs):
        uid, delta, reason = self._norm(*args, **kwargs)
        await self._write_verbose(uid, delta, reason or "xp_add")

    @commands.Cog.listener("satpam_xp")
    async def satpam_xp(self, *args, **kwargs):
        uid, delta, reason = self._norm(*args, **kwargs)
        await self._write_verbose(uid, delta, reason or "satpam_xp")

    @commands.Cog.listener("xp_award")
    async def xp_award(self, *args, **kwargs):
        uid, delta, reason = self._norm(*args, **kwargs)
        await self._write_verbose(uid, delta, reason or "xp_award")

async def setup(bot):
    await bot.add_cog(XpUpstashVerbose(bot))

def setup(bot):
    try:
        import asyncio
        if asyncio.get_event_loop().is_running():
            return asyncio.create_task(bot.add_cog(XpUpstashVerbose(bot)))
    except Exception:
        pass
    return bot.add_cog(XpUpstashVerbose(bot))