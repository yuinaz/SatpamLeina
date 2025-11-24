
from __future__ import annotations
import asyncio, logging, time
from typing import Optional
from discord.ext import commands
from satpambot.config.auto_defaults import cfg_str, cfg_int

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

log = logging.getLogger(__name__)

# === Module-env driven settings (fall back handled by cfg_* ===
PROBE_INTERVAL_SEC = cfg_int("UPSTASH_PROBE_INTERVAL_SEC", 1800)   # 30 minutes
BACKOFF_ON_FAIL_SEC = cfg_int("UPSTASH_BACKOFF_ON_FAIL_SEC", 3600) # 60 minutes
FAILOVER_ENABLE     = cfg_int("UPSTASH_FAILOVER_ENABLE", 1)        # 1=on, 0=off

class UpstashFailoverAndResync(commands.Cog):
    """
    - Wraps XpEventBridgeOverlay._incr and XpStageUpstashMirrorOverlay._upstash_set
      to detect failure (quota/429/400) and enter degraded mode.
    - While degraded: all Upstash writes are NO-OP; pinned JSON remains the source of truth.
    - Background task probes Upstash; when back, sync pinned -> Upstash, re-enable writes.
    - All timings & toggles come from module env (cfg_*).
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.degraded = False
        self.next_probe_ts = 0.0
        self.url = cfg_str("UPSTASH_REDIS_REST_URL","")
        self.token = cfg_str("UPSTASH_REDIS_REST_TOKEN","")
        self.total_key = cfg_str("XP_SENIOR_KEY","xp:bot:senior_total")
        self._bg_task = None

    async def cog_load(self):
        if not FAILOVER_ENABLE:
            log.info("[upstash-failover] disabled via UPSTASH_FAILOVER_ENABLE")
            return
        self._wrap_targets()
        self._bg_task = asyncio.create_task(self._probe_loop(), name="upstash_failover_probe")

    def cog_unload(self):
        if self._bg_task and not self._bg_task.done():
            self._bg_task.cancel()

    # ---------- Wrapping existing cogs ----------
    def _wrap_targets(self):
        for name in list(self.bot.cogs.keys()):
            cog = self.bot.cogs.get(name)
            if cog is None: continue
            cname = cog.__class__.__name__
            if cname == "XpEventBridgeOverlay" and hasattr(cog, "_incr"):
                self._wrap_method(cog, "_incr", self._guarded_call_incr)
            if cname == "XpStageUpstashMirrorOverlay" and hasattr(cog, "_upstash_set"):
                self._wrap_method(cog, "_upstash_set", self._guarded_call_set)

    def _wrap_method(self, obj, method_name: str, replacement):
        orig = getattr(obj, method_name, None)
        if not orig or getattr(orig, "_ufr_wrapped", False):
            return
        async def wrapper(*a, **k):
            return await replacement(orig, *a, **k)
        wrapper._ufr_wrapped = True  # type: ignore
        setattr(obj, method_name, wrapper)
        log.info("[upstash-failover] wrapped %s.%s", obj.__class__.__name__, method_name)

    async def _guarded_call_incr(self, orig, *a, **k):
        if self.degraded or not self.url or not self.token:
            return None
        try:
            return await orig(*a, **k)
        except Exception as e:
            self._enter_degraded(e)
            return None

    async def _guarded_call_set(self, orig, *a, **k):
        if self.degraded or not self.url or not self.token:
            return None
        try:
            return await orig(*a, **k)
        except Exception as e:
            self._enter_degraded(e)
            return None

    def _enter_degraded(self, e: Exception):
        self.degraded = True
        self.next_probe_ts = time.time() + BACKOFF_ON_FAIL_SEC
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            kv = PinnedJSONKV(self.bot)
            self.bot.loop.create_task(kv.set_multi({
                "upstash:degraded": 1,
                "upstash:last_error": str(e)[:200],
                "upstash:next_probe": int(self.next_probe_ts)
            }))
        except Exception:
            pass
        log.warning("[upstash-failover] degraded due to: %r; next probe in %ds",
                    e, BACKOFF_ON_FAIL_SEC)

    # ---------- Probing & resync ----------
    async def _probe_loop(self):
        while True:
            try:
                await asyncio.sleep(5)
                if not self.degraded:
                    self._wrap_targets()  # catch late-loaded cogs
                now = time.time()
                if not self.degraded and self.url and self.token and now - self.next_probe_ts > PROBE_INTERVAL_SEC:
                    self.next_probe_ts = now
                    await self._probe_once()
                if self.degraded and now >= self.next_probe_ts:
                    ok = await self._probe_once()
                    if ok:
                        await self._resync_from_pinned()
                        self.degraded = False
                        log.info("[upstash-failover] Upstash healthy again; writes re-enabled")
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.debug("[upstash-failover] loop err: %r", e)

    async def _probe_once(self) -> bool:
        if not self.url or not self.token:
            return False
        try:
            import aiohttp
            async with aiohttp.ClientSession() as s:
                u = f"{self.url}/get/{self.total_key}"
                async with s.get(u, headers={"Authorization": f"Bearer {self.token}"} ) as r:
                    if r.status != 200:
                        return False
                    _ = await r.json()
                    return True
        except Exception:
            return False

    async def _resync_from_pinned(self):
        try:
            import aiohttp
            from urllib.parse import quote
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            kv = PinnedJSONKV(self.bot)
            m = await kv.get_map()
            keys = [
                self.total_key,
                "xp:stage:label", "xp:stage:current", "xp:stage:required", "xp:stage:percent",
                "learning:status", "learning:status_json",
            ]
            async with aiohttp.ClientSession() as s:
                for k in keys:
                    if k in m and m[k] is not None:
                        val = str(m[k])
                        u = f"{self.url}/set/{quote(str(k), safe='')}/{quote(val, safe='')}"
                        async with s.get(u, headers={"Authorization": f"Bearer {self.token}"} ) as r:
                            if r.status != 200:
                                txt = await r.text()
                                raise RuntimeError(f"HTTP {r.status}: {txt}")
            await kv.set_multi({"upstash:degraded": 0})
            log.info("[upstash-failover] resynced %d keys from pinned JSON to Upstash", len(keys))
        except Exception as e:
            self.degraded = True
            self.next_probe_ts = time.time() + BACKOFF_ON_FAIL_SEC
            log.warning("[upstash-failover] resync failed: %r; stay degraded", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(UpstashFailoverAndResync(bot))
