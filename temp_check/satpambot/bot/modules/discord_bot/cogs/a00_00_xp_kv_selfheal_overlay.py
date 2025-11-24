from __future__ import annotations
import asyncio, logging, os, json, re
from typing import Optional, Any, Dict, List
try:
    import aiohttp
except Exception as _e:
    aiohttp = None  # type: ignore
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
ENABLE = os.getenv("XP_KV_SELFHEAL_ENABLE", "1") == "1"
INTERVAL = float(os.getenv("XP_KV_SELFHEAL_INTERVAL_SEC", "15"))
CONNECT_TIMEOUT = float(os.getenv("UPSTASH_CONNECT_TIMEOUT_SEC", "1.8"))
READ_TIMEOUT = float(os.getenv("UPSTASH_READ_TIMEOUT_SEC", "1.8"))

# Keys we keep healthy
XP_TOTAL_KEY = os.getenv("XP_TOTAL_KEY","xp:bot:senior_total")
XP_STAGE_LABEL_KEY = os.getenv("XP_STAGE_LABEL_KEY","xp:stage:label")
XP_STAGE_CURRENT_KEY = os.getenv("XP_STAGE_CURRENT_KEY","xp:stage:current")
XP_STAGE_REQUIRED_KEY = os.getenv("XP_STAGE_REQUIRED_KEY","xp:stage:required")
XP_STAGE_PERCENT_KEY = os.getenv("XP_STAGE_PERCENT_KEY","xp:stage:percent")

_KEYS = [XP_TOTAL_KEY, XP_STAGE_LABEL_KEY, XP_STAGE_CURRENT_KEY, XP_STAGE_REQUIRED_KEY, XP_STAGE_PERCENT_KEY]

def _smart_coerce(raw: str) -> Optional[int]:
    try:
        j = json.loads(raw)
        if isinstance(j, dict):
            for k in ("senior_total","total","xp","value"):
                if k in j:
                    try: return int(float(j[k]))
                    except Exception: pass
        if isinstance(j, (int, float)): return int(j)
        if isinstance(j, str):
            return int(float(j))
    except Exception:
        pass
    # largest integer substring
    m = re.findall(r"-?\d+", str(raw))
    if not m: return None
    try:
        nums = [int(x) for x in m]
        return max(nums, key=abs)
    except Exception:
        return None

async def _fetch_upstash(keys: List[str]) -> Dict[str, Optional[str]]:
    if not (UPSTASH_URL and UPSTASH_TOKEN and aiohttp):
        return {k: None for k in keys}
    headers = {"Authorization": f"Bearer {UPSTASH_TOKEN}"}
    payload = {"pipeline": [[ "GET", k ] for k in keys]}
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=CONNECT_TIMEOUT, sock_read=READ_TIMEOUT)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.post(f"{UPSTASH_URL}/pipeline", headers=headers, json=payload) as resp:
                if resp.status != 200:
                    log.info("[xp-kv-selfheal] upstash non-200: %s", resp.status)
                    return {k: None for k in keys}
                data = await resp.json()
                out: Dict[str, Optional[str]] = {}
                for k, row in zip(keys, data):
                    try:
                        out[k] = None if row is None else (row.get("result") if isinstance(row, dict) else None)
                    except Exception:
                        out[k] = None
                return out
    except Exception as e:
        log.info("[xp-kv-selfheal] upstash fetch failed: %r", e)
        return {k: None for k in keys}

async def _set_upstash(pairs: Dict[str, Any]) -> None:
    if not (UPSTASH_URL and UPSTASH_TOKEN and aiohttp): return
    headers = {"Authorization": f"Bearer {UPSTASH_TOKEN}"}
    cmds = [[ "SET", k, str(v) ] for k, v in pairs.items()]
    if not cmds: return
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=CONNECT_TIMEOUT, sock_read=READ_TIMEOUT)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.post(f"{UPSTASH_URL}/pipeline", headers=headers, json={"pipeline": cmds}) as resp:
                if resp.status != 200:
                    log.info("[xp-kv-selfheal] upstash set non-200: %s", resp.status)
    except Exception as e:
        log.info("[xp-kv-selfheal] upstash set failed: %r", e)

class XpKvSelfhealOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if ENABLE:
            self.task.start()

    @tasks.loop(seconds=INTERVAL)
    async def task(self):
        
        import os
        if os.getenv('LEINA_SHUTTING_DOWN') == '1':
            return None
# never block the event loop if network is slow
        try:
            vals = await _fetch_upstash(_KEYS)
            fixes: Dict[str, Any] = {}
            # Only coerce the numeric fields; label/percent are left intact
            for k in (XP_TOTAL_KEY, XP_STAGE_CURRENT_KEY, XP_STAGE_REQUIRED_KEY):
                raw = vals.get(k)
                if raw is None: 
                    continue
                coerced = _smart_coerce(raw)
                if coerced is None: 
                    continue
                # if the stored raw is not exactly the coerced int, write back the int
                try:
                    if str(int(raw)) != str(coerced):
                        fixes[k] = coerced
                except Exception:
                    fixes[k] = coerced
            if fixes:
                await _set_upstash(fixes)
                for k, v in fixes.items():
                    log.warning("[xp-kv-selfheal] coerced %s -> %s", k, v)
        except Exception as e:
            log.info("[xp-kv-selfheal] task err: %r", e)

    @task.before_loop
    async def _delay(self):
        await asyncio.sleep(6.0)

async def setup(bot): 
    try:
        await bot.add_cog(XpKvSelfhealOverlay(bot))
    except Exception as e:
        log.info("[xp-kv-selfheal] setup swallowed: %r", e)

    def cog_unload(self):
        try: self.task.cancel()
        except Exception: pass
