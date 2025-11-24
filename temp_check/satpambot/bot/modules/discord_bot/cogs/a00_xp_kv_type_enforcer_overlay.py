
from __future__ import annotations
import os, json, logging, urllib.request
from typing import Optional
from discord.ext import commands

log = logging.getLogger(__name__)

def _env(k: str, d: Optional[str]=None) -> Optional[str]:
    v=os.getenv(k); return v if v not in (None,"") else d

def _pipe(cmds):
    base=_env("UPSTASH_REDIS_REST_URL"); tok=_env("UPSTASH_REDIS_REST_TOKEN")
    if not base or not tok: return None
    body=json.dumps(cmds).encode("utf-8")
    req=urllib.request.Request(f"{base}/pipeline", method="POST", data=body)
    req.add_header("Authorization", f"Bearer {tok}"); req.add_header("Content-Type","application/json")
    with urllib.request.urlopen(req, timeout=3.5) as r:
        return json.loads(r.read().decode("utf-8","ignore"))

def _intish(raw) -> Optional[int]:
    try:
        if isinstance(raw, int): return raw
        s = str(raw or "").strip()
        if not s: return None
        if s.startswith('{'):
            j = json.loads(s)
            for k in ("senior_total","senior_total_xp","total","value","v"):
                if k in j:
                    return int(j[k])
            return None
        # first signed integer token
        num = []
        for ch in s:
            if ch in "+-" and not num:
                num.append(ch)
            elif ch.isdigit():
                num.append(ch)
            else:
                break
        return int("".join(num)) if num else None
    except Exception:
        return None

class XpKvTypeEnforcerOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.key = os.getenv("XP_TOTAL_KEY") or "xp:bot:senior_total"
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            r = _pipe([["GET", self.key], ["GET", "learning:status_json"]])
            cur_raw = (r[0] or {}).get("result")
            # Already integer? enforce set as integer string (Upstash numeric)
            cur = _intish(cur_raw)
            stat_raw = (r[1] or {}).get("result")
            stat_total = None
            try:
                j = json.loads(stat_raw) if isinstance(stat_raw, str) else stat_raw
                if isinstance(j, dict):
                    st = j.get("senior_total")
                    if isinstance(st, (int, str)):
                        stat_total = _intish(st)
            except Exception:
                pass
            target = cur if isinstance(cur,int) else stat_total
            if isinstance(target,int):
                _pipe([["SET", self.key, str(target)]])
                log.info("[xp-type] enforced integer key %s=%s", self.key, target)
            else:
                log.warning("[xp-type] cannot determine integer for %s (cur=%r stat=%r)", self.key, cur_raw, stat_raw)
        except Exception as e:
            log.debug("[xp-type] no-op: %r", e)

async def setup(bot):
    await bot.add_cog(XpKvTypeEnforcerOverlay(bot))
