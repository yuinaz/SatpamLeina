from __future__ import annotations

from discord.ext import commands
import json, random, logging, datetime as _dt
from pathlib import Path
import discord
from discord.ext import tasks
from satpambot.config.local_cfg import cfg

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[5]
DATA_DIR = ROOT / "data" / "neuro-lite"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE = DATA_DIR / "weekly_event_state.json"
PROGRESS = DATA_DIR / "progress.json"
JR = DATA_DIR / "learn_progress_junior.json"
SR = DATA_DIR / "learn_progress_senior.json"

REPORT_THREAD_IDS_DEFAULT = "1426397317598154844 1425400701982478408"
try:
    from satpambot.bot.modules.discord_bot.cogs.a24_progress_explicit_thread_overlay import relay as _relay
    REPORT_THREAD_IDS_DEFAULT = str(getattr(_relay, "PREFERRED_THREAD_ID", "")) or REPORT_THREAD_IDS_DEFAULT
except Exception:
    pass
REPORT_THREAD_IDS = [int(x) for x in str(cfg("XP_REPORT_THREAD_IDS", REPORT_THREAD_IDS_DEFAULT)).split() if x.isdigit()]

WEEKLY_EVENTS_PER_MONTH = int(cfg("XP_WEEKLY_EVENTS_PER_MONTH", "4") or 4)
WEEKEND_MULTIPLIER = float(cfg("XP_WEEKEND_MULTIPLIER", "3.0") or 3.0)
BASE_MIN = int(cfg("XP_WEEKLY_MIN", "10") or 10)
BASE_MAX = int(cfg("XP_WEEKLY_MAX", "100") or 100)
OVERALL_MODE = str(cfg("XP_OVERALL_MODE", "per_leaf")).strip()  # per_leaf | per_award

def _now():
    return _dt.datetime.utcnow()

def _week_id(dt: _dt.datetime) -> str:
    iso = dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"

def _load_json(p: Path, default):
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default

def _dump_json(p: Path, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _iter_leaves(d: dict):
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            for lk, lv in v.items():
                if isinstance(lv, (int, float)):
                    yield (k, lk)

def _award_curriculum(path: Path, amount: int):
    data = _load_json(path, {"overall": 0})
    leaves = list(_iter_leaves(data))
    if not leaves:
        data["overall"] = int(data.get("overall", 0) or 0) + amount
    else:
        for k, lk in leaves:
            data.setdefault(k, {})
            cur = int(data[k].get(lk, 0) or 0)
            data[k][lk] = cur + amount
        if OVERALL_MODE == "per_award":
            data["overall"] = int(data.get("overall", 0) or 0) + amount
        else:  # per_leaf (default)
            data["overall"] = int(data.get("overall", 0) or 0) + amount * len(leaves)
    _dump_json(path, data)

def _award_progress(amount: int):
    p = _load_json(PROGRESS, {"xp": 0, "today": 0})
    p["xp"] = int(p.get("xp", 0) or 0) + amount
    p["today"] = int(p.get("today", 0) or 0) + amount
    p["last_bonus"] = amount
    p["last_bonus_ts"] = int(_now().timestamp())
    _dump_json(PROGRESS, p)

def _pick_schedule_for_week(dt: _dt.datetime) -> int:
    iso = dt.isocalendar()
    monday = dt - _dt.timedelta(days=iso.weekday-1)
    base = _dt.datetime(monday.year, monday.month, monday.day)
    hour = random.randint(0, 167)
    minute = random.choice([0, 15, 30, 45])
    ts = int((base + _dt.timedelta(hours=hour, minutes=minute)).timestamp())
    return ts

class WeeklyRandomXP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.state = _load_json(STATE, {})
        self.loop.start()

    def cog_unload(self):
        if self.loop.is_running():
            self.loop.cancel()

    @tasks.loop(minutes=30)
    async def loop(self):
        now = _now()
        wid = _week_id(now)
        st = self.state.get(wid) or {}
        if "scheduled_ts" not in st:
            st["scheduled_ts"] = _pick_schedule_for_week(now)
            st["triggered"] = False
            self.state[wid] = st
            _dump_json(STATE, self.state)

        if not st.get("triggered") and now.timestamp() >= st["scheduled_ts"]:
            base = min(max(BASE_MIN, 1), BASE_MAX)
            base = __import__("random").randint(BASE_MIN, BASE_MAX)
            dt_sched = _dt.datetime.utcfromtimestamp(st["scheduled_ts"])
            is_weekend = dt_sched.weekday() >= 5
            award = int(base * (WEEKEND_MULTIPLIER if is_weekend else 1.0))

            _award_progress(award)
            _award_curriculum(JR, award)
            _award_curriculum(SR, award)

            st["triggered"] = True
            st["award"] = award
            st["base"] = base
            st["weekend"] = bool(is_weekend)
            self.state[wid] = st
            _dump_json(STATE, self.state)

            await self._announce(award, base, is_weekend, wid)

    async def _announce(self, award: int, base: int, is_weekend: bool, wid: str):
        emb = discord.Embed(
            title="Weekly Random XP",
            description=f"Event mingguan untuk **{wid}** aktif!",
        )
        emb.add_field(name="Base", value=f"{base} XP", inline=True)
        if is_weekend and WEEKEND_MULTIPLIER != 1.0:
            emb.add_field(name="Weekend Bonus", value=f"x{WEEKEND_MULTIPLIER:g}", inline=True)
        emb.add_field(name="Total Bonus", value=f"**{award} XP per level**", inline=True)
        emb.set_footer(text="Bonus diterapkan penuh ke setiap level (junior & senior)")
        for ch_id in REPORT_THREAD_IDS:
            try:
                ch = self.bot.get_channel(ch_id)
                if ch:
                    await ch.send(embed=emb)
            except Exception as e:
                logging.getLogger(__name__).warning("[weekly_xp] announce failed for %s: %s", ch_id, e)

    @loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
async def setup(bot):
    await bot.add_cog(WeeklyRandomXP(bot))