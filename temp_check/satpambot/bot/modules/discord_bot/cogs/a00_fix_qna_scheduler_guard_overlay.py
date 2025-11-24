
from __future__ import annotations
import os, time, asyncio, logging, urllib.request, json, urllib.parse
from discord.ext import commands

log = logging.getLogger(__name__)

def _env(k, d=None):
    v = os.getenv(k)
    return v if v not in (None, "") else d

class _UpstashLite:
    def __init__(self):
        self.base = (_env("UPSTASH_REDIS_REST_URL","") or "").rstrip("/")
        self.tok = _env("UPSTASH_REDIS_REST_TOKEN","") or ""
        self.enabled = bool(self.base and self.tok)

    def _req(self, path: str):
        if not self.enabled: return None
        url = self.base + path
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.tok}"})
        with urllib.request.urlopen(req, timeout=10) as r:
            s = r.read().decode()
            try: return json.loads(s)
            except Exception: return {"result": s}

    async def setex(self, key: str, seconds: int, value: str="1"):
        try:
            val = urllib.parse.quote(value, safe="")
            k   = urllib.parse.quote(key, safe="")
            self._req(f"/set/{k}/{val}")
            self._req(f"/expire/{k}/{int(seconds)}")
            return True
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        try:
            k = urllib.parse.quote(key, safe="")
            r = self._req(f"/get/{k}")
            return r is not None and r.get("result") is not None
        except Exception:
            return False

class FixQnaSchedulerGuard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.us = _UpstashLite()

    def _patch(self, obj):
        # interval_sec default
        if not hasattr(obj, "interval_sec") or not isinstance(getattr(obj,"interval_sec"), (int, float)) or getattr(obj,"interval_sec") <= 0:
            try:
                obj.interval_sec = int(os.getenv("QNA_SEED_INTERVAL_SEC","180"))
            except Exception:
                obj.interval_sec = 180
            log.warning("[qna_autolearn_fix] set QnAAutoLearnScheduler.interval_sec=%s", obj.interval_sec)

        # add can_emit guard
        if not hasattr(obj, "can_emit"):
            def can_emit(now=None):
                if not getattr(obj, "enabled", True): return False
                try: now_ts = float(now) if now is not None else time.time()
                except Exception: now_ts = time.time()
                last = float(getattr(obj, "last_emit_at", 0) or 0.0)
                return (now_ts - last) >= float(getattr(obj, "interval_sec", 180) or 180)
            obj.can_emit = can_emit

        # idempotency via Upstash
        if not hasattr(obj, "_emit_gate_key"):
            obj._emit_gate_key = "qna:seed:gate"

        async def _emit_once(fn):
            gate = f"{obj._emit_gate_key}"
            if self.us.enabled and await self.us.exists(gate):
                return False
            # set a short TTL gate ~= interval
            if self.us.enabled:
                await self.us.setex(gate, int(getattr(obj,"interval_sec",180) or 180))
            try:
                await fn()
                obj.last_emit_at = time.time()
                return True
            except Exception as e:
                log.warning("[qna_autolearn_fix] emit failed: %r", e)
                return False

        obj._emit_once = _emit_once

    @commands.Cog.listener()
    async def on_cog_add(self, cog):
        name = type(cog).__name__.lower()
        if "qna" in name and "scheduler" in name:
            try:
                self._patch(cog)
                log.info("[qna_autolearn_fix] guard attached to %s", type(cog).__name__)
            except Exception as e:
                log.warning("[qna_autolearn_fix] patch error: %r", e)

def _inject(bot):
    flag = "_fix_qna_scheduler_guard_loaded"
    if getattr(bot, flag, False): return
    setattr(bot, flag, True)
    try:
        bot.add_cog(FixQnaSchedulerGuard(bot))
        log.info("[qna_autolearn_fix] guard overlay loaded")
    except Exception:
        FixQnaSchedulerGuard(bot)

def setup(bot): _inject(bot)
async def setup(bot): _inject(bot)
