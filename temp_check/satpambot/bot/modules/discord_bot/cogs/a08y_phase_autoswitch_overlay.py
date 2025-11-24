
from __future__ import annotations
import os, json, asyncio, logging
from typing import Any, Dict, Optional

try:
    from discord.ext import commands
except Exception as _e:
    commands = None  # type: ignore
    _IMPORT_ERR = _e
else:
    _IMPORT_ERR = None

log = logging.getLogger(__name__)

# ---- ENV ----
ENABLE = (os.getenv("PHASE_AUTOSWITCH_ENABLE","1")=="1")
INTERVAL_SEC = int(os.getenv("PHASE_AUTOSWITCH_INTERVAL_SEC","120"))
LADDER_JSON_PATH = os.getenv("PHASE_AUTOSWITCH_LADDER_JSON_PATH","data/config/ladder.json")
# Labels & tiers
KULIAH_LABEL = os.getenv("PHASE_KULIAH_LABEL","KULIAH")
MAGANG_LABEL = os.getenv("PHASE_MAGANG_LABEL","MAGANG")
MAGANG_TIER  = os.getenv("PHASE_MAGANG_TIER","1TH")
ENABLE_WORK_SWITCH = (os.getenv("PHASE_ENABLE_WORK_SWITCH","0")=="1")  # LOCK by default
WORK_LABEL = os.getenv("PHASE_WORK_LABEL","KERJA")
PHASE_WORK_REQUIRED_TOTAL = int(os.getenv("PHASE_WORK_REQUIRED_TOTAL", "0") or "0")
# KV keys
XP_TOTAL_KEY = os.getenv("XP_TOTAL_KEY","xp:bot:senior_total")
XP_STAGE_LABEL_KEY = os.getenv("XP_STAGE_LABEL_KEY","xp:stage:label")
XP_STAGE_CURRENT_KEY = os.getenv("XP_STAGE_CURRENT_KEY","xp:stage:current")
XP_STAGE_REQUIRED_KEY = os.getenv("XP_STAGE_REQUIRED_KEY","xp:stage:required")
XP_STAGE_PERCENT_KEY = os.getenv("XP_STAGE_PERCENT_KEY","xp:stage:percent")
LEARNING_STATUS = os.getenv("LEARNING_STATUS_KEY","learning:status")
LEARNING_STATUS_JSON = os.getenv("LEARNING_STATUS_JSON_KEY","learning:status_json")
# Optional pin mirror
PHASE_PIN_CHANNEL_ID = int(os.getenv("PHASE_PIN_CHANNEL_ID","0") or 0)
PHASE_PIN_MESSAGE_ID = int(os.getenv("PHASE_PIN_MESSAGE_ID","0") or 0)

def _kv_iface(bot: Any):
    store = getattr(bot, "_memkv", None) or getattr(bot, "memkv", None)
    if store is None:
        store = {}
        setattr(bot, "_memkv", store)
    return store

async def _kv_get(bot: Any, key: str) -> Optional[str]:
    kv = _kv_iface(bot)
    try:
        if hasattr(kv, "get"):
            v = kv.get(key)
            if asyncio.iscoroutine(v):
                v = await v
            if isinstance(v, dict) and "result" in v:
                v = v["result"]
            return None if v is None else str(v)
        return None if key not in kv else str(kv[key])
    except Exception:
        return None

async def _kv_set(bot: Any, key: str, val: Any) -> bool:
    kv = _kv_iface(bot)
    try:
        if hasattr(kv, "set"):
            r = kv.set(key, val)
            if asyncio.iscoroutine(r):
                await r
            return True
        kv[key] = val
        return True
    except Exception:
        return False

def _as_int(s: Optional[str], default:int=0) -> int:
    if s is None: return default
    try:
        return int(float(s))
    except Exception:
        return default

def _pct(cur:int, req:int) -> float:
    if req <= 0: return 0.0
    p = max(0.0, min(100.0, (cur/req)*100.0))
    return round(p, 1)

def _load_ladder(path:str) -> Dict[str,Any]:
    try:
        with open(path,"r",encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception as e:
        log.warning("[phase-auto] ladder read fail %r -> fallback empty", e)
        return {}

def _kuliah_top_req(ld: Dict[str,Any]) -> int:
    try:
        kou = ld.get("senior",{}).get(KULIAH_LABEL,{})
        if isinstance(kou, dict):
            vals = []
            for v in kou.values():
                try: vals.append(int(float(v)))
                except Exception: pass
            return max(vals) if vals else 0
    except Exception:
        pass
    return 0

def _magang_req(ld: Dict[str,Any]) -> int:
    try:
        mg = ld.get("senior",{}).get(MAGANG_LABEL,{})
        if isinstance(mg, dict):
            v = mg.get(MAGANG_TIER)
            if isinstance(v,(int,float,str)):
                return int(float(v))
    except Exception:
        pass
    return 0

def _work_req(ld: Dict[str,Any]) -> int:
    # Try ladder["senior"]["KERJA"] in various shapes; else use PHASE_WORK_REQUIRED_TOTAL
    try:
        wk = ld.get("senior",{}).get(WORK_LABEL, None)
        if isinstance(wk, dict):
            vals = []
            for v in wk.values():
                try: vals.append(int(float(v)))
                except Exception: pass
            if vals: return max(vals)
        elif isinstance(wk, (int,float,str)):
            try: return int(float(wk))
            except Exception: pass
    except Exception:
        pass
    # fallback
    if PHASE_WORK_REQUIRED_TOTAL > 0:
        return PHASE_WORK_REQUIRED_TOTAL
    return 0

class PhaseAutoSwitchOverlay(commands.Cog):  # type: ignore[misc]
    """Auto-switch KULIAH → MAGANG using ladder.json thresholds.
       Optionally switch MAGANG → KERJA if PHASE_ENABLE_WORK_SWITCH=1 (locked by default)."""
    def __init__(self, bot: Any):
        self.bot = bot
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self._ladder: Dict[str,Any] = {}

    async def cog_load(self):
        if not ENABLE:
            log.info("[phase-auto] disabled"); return
        await asyncio.sleep(3)
        self._ladder = _load_ladder(LADDER_JSON_PATH)
        await self._recompute_and_apply("startup")
        self._task = self.bot.loop.create_task(self._looper(), name="phase_autoswitch")

    async def cog_unload(self):
        if self._task and not self._task.done():
            self._stop.set(); self._task.cancel()
            try: await self._task
            except asyncio.CancelledError: pass

    async def _looper(self):
        await asyncio.sleep(5)
        while not self._stop.is_set():
            try:
                await self._recompute_and_apply("periodic")
            except Exception:
                log.exception("[phase-auto] loop error")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=INTERVAL_SEC)
            except asyncio.TimeoutError:
                pass

    async def on_xp_add(self, *args: Any, **kwargs: Any):
        try:
            await self._recompute_and_apply("xp_add")
        except Exception:
            log.exception("[phase-auto] on_xp_add failed")

    def on_hotenv_reload(self, *a, **kw):
        if self.bot and self.bot.loop:
            self.bot.loop.create_task(self._reload_ladder_and_recompute())

    async def _reload_ladder_and_recompute(self):
        self._ladder = _load_ladder(LADDER_JSON_PATH)
        await self._recompute_and_apply("hotenv")

    async def _recompute_and_apply(self, ctx: str):
        total = _as_int(await _kv_get(self.bot, XP_TOTAL_KEY), 0)
        label_raw = await _kv_get(self.bot, XP_STAGE_LABEL_KEY)
        label = (label_raw or "").upper()

        kuliah_top = _kuliah_top_req(self._ladder)
        magang_req = _magang_req(self._ladder)
        work_req   = _work_req(self._ladder)

        # Validate ladder basics
        if kuliah_top <= 0 or magang_req <= 0:
            log.warning("[phase-auto] ladder invalid; kuliah_top=%s magang_req=%s", kuliah_top, magang_req)
            return

        # KULIAH -> MAGANG
        if label.startswith(KULIAH_LABEL) and total >= kuliah_top:
            pct = _pct(total, magang_req)
            await _kv_set(self.bot, XP_STAGE_LABEL_KEY, MAGANG_LABEL)
            await _kv_set(self.bot, XP_STAGE_CURRENT_KEY, f"{total}")
            await _kv_set(self.bot, XP_STAGE_REQUIRED_KEY, f"{magang_req}")
            await _kv_set(self.bot, XP_STAGE_PERCENT_KEY, f"{pct}")
            await _kv_set(self.bot, LEARNING_STATUS, f"{MAGANG_LABEL} ({pct}%)")
            await _kv_set(self.bot, LEARNING_STATUS_JSON, json.dumps({
                "label": MAGANG_LABEL, "percent": pct,
                "remaining": max(0, magang_req - total),
                "senior_total": total,
                "stage": { "kuliah_top": kuliah_top, "magang_req": magang_req, "work_req": work_req, "current": total }
            }))
            await self._maybe_edit_pin(fase=MAGANG_LABEL, pct=pct, total=total, req=magang_req)
            try:
                self.bot.dispatch("phase_switched", MAGANG_LABEL, pct, total)
                self.bot.dispatch("hotenv_reload")
            except Exception:
                pass
            log.warning("[phase-auto] %s -> SWITCH to %s (%.1f%%) total=%s req=%s", ctx, MAGANG_LABEL, pct, total, magang_req)
            return

        # MAGANG -> KERJA (only if unlocked)
        if ENABLE_WORK_SWITCH and label.startswith(MAGANG_LABEL) and work_req > 0 and total >= work_req:
            pct = _pct(total, work_req)
            await _kv_set(self.bot, XP_STAGE_LABEL_KEY, WORK_LABEL)
            await _kv_set(self.bot, XP_STAGE_CURRENT_KEY, f"{total}")
            await _kv_set(self.bot, XP_STAGE_REQUIRED_KEY, f"{work_req}")
            await _kv_set(self.bot, XP_STAGE_PERCENT_KEY, f"{pct}")
            await _kv_set(self.bot, LEARNING_STATUS, f"{WORK_LABEL} ({pct}%)")
            await _kv_set(self.bot, LEARNING_STATUS_JSON, json.dumps({
                "label": WORK_LABEL, "percent": pct,
                "remaining": max(0, work_req - total),
                "senior_total": total,
                "stage": { "kuliah_top": kuliah_top, "magang_req": magang_req, "work_req": work_req, "current": total }
            }))
            await self._maybe_edit_pin(fase=WORK_LABEL, pct=pct, total=total, req=work_req)
            try:
                self.bot.dispatch("phase_switched", WORK_LABEL, pct, total)
                self.bot.dispatch("hotenv_reload")
            except Exception:
                pass
            log.warning("[phase-auto] %s -> SWITCH to %s (%.1f%%) total=%s req=%s", ctx, WORK_LABEL, pct, total, work_req)
            return

        # Keep percentage in sync for current label
        req = _as_int(await _kv_get(self.bot, XP_STAGE_REQUIRED_KEY), 0)
        cur = _as_int(await _kv_get(self.bot, XP_STAGE_CURRENT_KEY), 0)
        base_req = req or (work_req if label.startswith(WORK_LABEL) else (magang_req if label.startswith(MAGANG_LABEL) else kuliah_top))
        base_cur = cur or total
        pct = _pct(base_cur, base_req)
        await _kv_set(self.bot, XP_STAGE_PERCENT_KEY, f"{pct}")
        await _kv_set(self.bot, LEARNING_STATUS, f"{(label_raw or KULIAH_LABEL)} ({pct}%)")
        await _kv_set(self.bot, LEARNING_STATUS_JSON, json.dumps({
            "label": label_raw or KULIAH_LABEL, "percent": pct,
            "remaining": max(0, base_req - base_cur),
            "senior_total": total,
            "stage": { "kuliah_top": kuliah_top, "magang_req": magang_req, "work_req": work_req, "current": base_cur }
        }))
        await self._maybe_edit_pin(fase=(label_raw or KULIAH_LABEL), pct=pct, total=total, req=base_req)
        log.info("[phase-auto] %s -> keep %s (%.1f%%) total=%s", ctx, label_raw or KULIAH_LABEL, pct, total)

    async def _maybe_edit_pin(self, fase: str, pct: float, total: int, req: int):
        if not (PHASE_PIN_CHANNEL_ID and PHASE_PIN_MESSAGE_ID):
            return
        try:
            ch = self.bot.get_channel(PHASE_PIN_CHANNEL_ID) or await self.bot.fetch_channel(PHASE_PIN_CHANNEL_ID)
            msg = await ch.fetch_message(PHASE_PIN_MESSAGE_ID)
            content = f"**Learning:** {fase} ({pct}%)\\n• total={total} / req={req}"
            await msg.edit(content=content)
        except Exception:
            pass

    # Commands
    @commands.command(name="phase_status")  # type: ignore[attr-defined]
    @commands.is_owner()                    # type: ignore[attr-defined]
    async def phase_status_cmd(self, ctx: Any):
        total = int((await _kv_get(self.bot, XP_TOTAL_KEY) or "0"))
        lbl = (await _kv_get(self.bot, XP_STAGE_LABEL_KEY)) or "(unknown)"
        req = int((await _kv_get(self.bot, XP_STAGE_REQUIRED_KEY) or "0"))
        pct = (await _kv_get(self.bot, XP_STAGE_PERCENT_KEY) or "0")
        await ctx.reply(f"[phase-auto] label={lbl} total={total} req={req} pct={pct}%")

    @commands.command(name="phase_fix")  # type: ignore[attr-defined]
    @commands.is_owner()                 # type: ignore[attr-defined]
    async def phase_fix_cmd(self, ctx: Any):
        await self._recompute_and_apply("manual")
        await ctx.reply("[phase-auto] recomputed")

async def setup(bot: Any):
    if _IMPORT_ERR is not None:
        raise _IMPORT_ERR
    await bot.add_cog(PhaseAutoSwitchOverlay(bot))

def setup(bot: Any):
    if _IMPORT_ERR is not None:
        raise _IMPORT_ERR
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(bot.add_cog(PhaseAutoSwitchOverlay(bot)))
            return
    except Exception:
        pass
    bot.add_cog(PhaseAutoSwitchOverlay(bot))
