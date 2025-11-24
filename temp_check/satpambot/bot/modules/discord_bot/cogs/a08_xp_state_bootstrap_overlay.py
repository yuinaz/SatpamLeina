from discord.ext import commands
from discord.ext import tasks

import os, logging
from discord.ext import commands, tasks

def _intish(x, default=0):
    if x is None:
        return default
    try:
        return int(x)
    except Exception:
        s = str(x).strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                obj = json.loads(s)
                for k in ("senior_total_xp","value","v"):
                    if k in obj:
                        return int(obj[k])
            except Exception:
                pass
        digits = "".join(ch for ch in s if ch.isdigit())
        return int(digits or default)
try:
    import httpx
except Exception:
    httpx = None

log = logging.getLogger(__name__)
UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
PHASE_KEY = os.getenv("LEARNING_PHASE_KEY","learning:phase")
TK_KEY = os.getenv("TK_XP_KEY","xp:bot:tk_total")
SR_KEY = os.getenv("SENIOR_XP_KEY","xp:bot:senior_total")
REFRESH_MIN = int(os.getenv("XP_STATE_REFRESH_MIN","10"))
DEFAULT_PHASE = os.getenv("LEARNING_PHASE_DEFAULT","tk")

async def _get(client, key):
    r = await client.get(f"{UPSTASH_URL}/get/{key}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"})
    if r.status_code == 200:
        return (r.json() or {}).get("result")

class XPStateBootstrap(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._client = httpx.AsyncClient(timeout=8.0) if httpx else None
        self.refresh.start()

    @tasks.loop(minutes=REFRESH_MIN)
    async def refresh(self):
        if not (UPSTASH_URL and UPSTASH_TOKEN and self._client):
            self.bot._xp_state = {"phase": DEFAULT_PHASE, "tk_total": 0, "senior_total": 0}
            return
        try:
            phase = await _get(self._client, PHASE_KEY)
            tk_total = await _get(self._client, TK_KEY)
            sr_total = await _get(self._client, SR_KEY)
            self.bot._xp_state = {
                "phase": (phase or DEFAULT_PHASE),
                "tk_total": _intish(tk_total or 0),
                "senior_total": _intish(sr_total or 0),
            }
            log.info("[xp-state] phase=%s tk_total=%s senior_total=%s",
                     self.bot._xp_state["phase"], self.bot._xp_state["tk_total"], self.bot._xp_state["senior_total"])
        except Exception as e:
            log.warning("[xp-state] refresh fail: %r", e)

    @refresh.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(XPStateBootstrap(bot))