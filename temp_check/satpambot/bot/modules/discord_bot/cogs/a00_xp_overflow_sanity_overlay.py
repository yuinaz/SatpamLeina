
from __future__ import annotations
import os, json, logging, urllib.request
from typing import Optional
from discord.ext import commands

log = logging.getLogger(__name__)

def _env(k: str, d: Optional[str]=None) -> Optional[str]:
    v = os.getenv(k); return v if v not in (None,"") else d

def _pipe(cmds):
    base=_env("UPSTASH_REDIS_REST_URL"); tok=_env("UPSTASH_REDIS_REST_TOKEN")
    if not base or not tok: return None
    body=json.dumps(cmds).encode("utf-8")
    req=urllib.request.Request(f"{base}/pipeline", method="POST", data=body)
    req.add_header("Authorization", f"Bearer {tok}"); req.add_header("Content-Type","application/json")
    with urllib.request.urlopen(req, timeout=4.0) as r:
        return json.loads(r.read().decode("utf-8","ignore"))

def _intish(x) -> Optional[int]:
    try:
        if isinstance(x, int): return x
        s = str(x).strip()
        if s.startswith('{'):
            j = json.loads(s)
            for k in ("senior_total","senior_total_xp","total","value","v"):
                if k in j:
                    return int(j[k])
            return None
        # strip anything after first non-digit
        i=0; n=len(s); out=[]
        for ch in s:
            if ch in "+-" and i==0:
                out.append(ch)
            elif ch.isdigit():
                out.append(ch)
            elif ch in " \t\r\n":
                pass
            else:
                break
            i+=1
        if not out: return None
        return int("".join(out))
    except Exception:
        return None

def _get(k: str) -> Optional[str]:
    r = _pipe([["GET", k]])
    try: return r and r[0].get("result")
    except Exception: return None

def _set(k: str, v: str):
    _pipe([["SET", k, v]])

class XpOverflowSanityOverlay(commands.Cog):
    """On boot, sanity-check xp:bot:senior_total and reset from learning:status_json if absurd."""
    def __init__(self, bot):
        self.bot = bot
        self.key = _env("XP_TOTAL_KEY","xp:bot:senior_total") or "xp:bot:senior_total"
        self.enabled = (_env("XP_OVERFLOW_SANITY_ENABLE","1") or "1") not in ("0","false","False")
        try:
            self.max_ratio = float(_env("XP_OVERFLOW_MAX_RATIO","50.0"))
        except Exception:
            self.max_ratio = 50.0
        log.info("[xp-sanity] enable=%s key=%s ratio<=%s", self.enabled, self.key, self.max_ratio)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.enabled: 
            return
        try:
            cur_raw = _get(self.key)
            cur = _intish(cur_raw)
            sj_raw = _get("learning:status_json")
            target = None
            if sj_raw:
                try:
                    j = json.loads(sj_raw)
                    target = _intish(j.get("senior_total") if isinstance(j, dict) else None)
                except Exception:
                    # status_json might itself be a JSON string inside string
                    try:
                        j = json.loads(str(sj_raw))
                        if isinstance(j, dict):
                            target = _intish(j.get("senior_total"))
                    except Exception:
                        target = None

            if target is None:
                log.warning("[xp-sanity] status_json missing senior_total; skip")
                return

            if cur is None:
                log.warning("[xp-sanity] xp total is non-int (%r) -> reset to %s", cur_raw, target)
                _set(self.key, str(target))
                return

            if cur < 0 or (self.max_ratio>0 and cur > int(target * self.max_ratio)):
                log.warning("[xp-sanity] absurd xp total=%s vs status_total=%s -> resetting", cur, target)
                _set(self.key, str(target))
            else:
                log.info("[xp-sanity] xp total looks sane: %s (status_total=%s)", cur, target)
        except Exception as e:
            log.debug("[xp-sanity] no-op: %r", e)

async def setup(bot):
    await bot.add_cog(XpOverflowSanityOverlay(bot))
