from __future__ import annotations

from discord.ext import commands

import asyncio, os, time, math, sqlite3, logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List, Dict

import discord
from discord.ext import tasks

log = logging.getLogger(__name__)

def _db_path() -> str:
    return os.getenv("NEUROLITE_MEMORY_DB",
        os.path.join(os.path.dirname(__file__), "..","..","..","..","data","memory.sqlite3"))

def _now_ts() -> int:
    return int(time.time())

def _day_bucket(ts: Optional[int]=None) -> int:
    if ts is None:
        ts = _now_ts()
    return int(ts - (ts % 86400))

def _open_db():
    path = _db_path()
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        try: os.makedirs(d, exist_ok=True)
        except Exception: pass
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con

def _ensure_meta(con: sqlite3.Connection):
    con.execute("""CREATE TABLE IF NOT EXISTS learning_progress_meta(
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    con.commit()

def _meta_get(con: sqlite3.Connection, key: str) -> Optional[str]:
    _ensure_meta(con)
    cur = con.execute("SELECT value FROM learning_progress_meta WHERE key=?", (key,))
    r = cur.fetchone()
    return r["value"] if r else None

def _meta_set(con: sqlite3.Connection, key: str, value: str):
    _ensure_meta(con)
    con.execute("INSERT INTO learning_progress_meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    con.commit()

def _ensure_snapshots(con: sqlite3.Connection):
    con.execute("""CREATE TABLE IF NOT EXISTS progress_snapshots(
        day_ts INTEGER PRIMARY KEY,
        total_sent INTEGER,
        total_success INTEGER,
        lex_total INTEGER
    )""")
    con.commit()

def _upsert_snapshot(con: sqlite3.Connection, day_ts: int, total_sent:int, total_success:int, lex_total:int):
    _ensure_snapshots(con)
    con.execute("""INSERT INTO progress_snapshots(day_ts,total_sent,total_success,lex_total)
                   VALUES (?,?,?,?)
                   ON CONFLICT(day_ts) DO UPDATE SET
                    total_sent=excluded.total_sent,
                    total_success=excluded.total_success,
                    lex_total=excluded.lex_total""",
                (int(day_ts), int(total_sent), int(total_success), int(lex_total)))
    con.commit()

def _read_sticker_stats(con: sqlite3.Connection) -> Tuple[int,int,Dict[str,Dict[str,int]]]:
    total_sent = total_success = 0
    per = {}
    try:
        cur = con.execute("SELECT emotion, sent_count, success_count FROM sticker_stats")
        for r in cur.fetchall():
            emo = r["emotion"] or "neutral"
            snt = int(r["sent_count"] or 0)
            suc = int(r["success_count"] or 0)
            total_sent += snt
            total_success += suc
            per[emo] = {"sent": snt, "success": suc}
    except Exception:
        pass
    return total_sent, total_success, per

def _count_sticker_sent_period(con: sqlite3.Connection, since_ts: int) -> int:
    try:
        cur = con.execute("SELECT COUNT(1) AS c FROM sticker_sent WHERE ts>=?", (int(since_ts),))
        r = cur.fetchone()
        return int(r["c"]) if r and r["c"] is not None else 0
    except Exception:
        return 0

def _slang_counts(con: sqlite3.Connection, since_ts: Optional[int]=None):
    total=pos=neg=0
    new_tokens=0
    try:
        cur = con.execute("SELECT COUNT(1) AS c, SUM(CASE WHEN pos>0 THEN 1 ELSE 0 END) AS p, SUM(CASE WHEN neg>0 THEN 1 ELSE 0 END) AS n FROM slang_lexicon")
        r = cur.fetchone()
        total = int(r["c"] or 0); pos = int(r["p"] or 0); neg = int(r["n"] or 0)
        if since_ts is not None:
            cur2 = con.execute("SELECT COUNT(1) AS c FROM slang_lexicon WHERE updated_ts>=?", (int(since_ts),))
            r2 = cur2.fetchone()
            new_tokens = int(r2["c"] or 0)
            return total, pos, neg, new_tokens
    except Exception:
        pass
    return total, pos, neg

def _daily_sent_series(con: sqlite3.Connection, days:int=7) -> List[Tuple[int,int]]:
    now = _now_ts()
    start = _day_bucket(now - (days-1)*86400)
    series = {start + i*86400: 0 for i in range(days)}
    try:
        cur = con.execute("""SELECT (ts - (ts % 86400)) AS day_ts, COUNT(1) AS c
                             FROM sticker_sent
                             WHERE ts >= ?
                             GROUP BY day_ts""", (int(start),))
        for r in cur.fetchall():
            day = int(r["day_ts"] or 0)
            if day in series:
                series[day] = int(r["c"] or 0)
    except Exception:
        pass
    return sorted(series.items())

def _weekly_deltas_from_snapshots(con: sqlite3.Connection, days:int=7):
    _ensure_snapshots(con)
    now = _now_ts()
    start = _day_bucket(now - (days-1)*86400)
    cur = con.execute("""SELECT day_ts,total_sent,total_success,lex_total
                         FROM progress_snapshots
                         WHERE day_ts >= ? ORDER BY day_ts ASC""", (int(start),))
    rows = cur.fetchall()
    if not rows:
        return (0,0,0,[])
    first = rows[0]
    last  = rows[-1]
    d_sent = int(last["total_sent"] - first["total_sent"])
    d_succ = int(last["total_success"] - first["total_success"])
    d_lex  = int(last["lex_total"] - first["lex_total"])
    per_day = []
    prev = None
    for r in rows:
        if prev is None:
            per_day.append((int(r["day_ts"]), 0))
        else:
            per_day.append((int(r["day_ts"]), max(0, int(r["total_success"] - prev["total_success"]))))
        prev = r
    return (d_sent, d_succ, d_lex, per_day)

_SPARK = "▁▂▃▄▅▆▇█"
def _sparkline(values: List[int]) -> str:
    if not values: return "—"
    m = max(values) or 1
    out = []
    for v in values:
        idx = int((v/m) * (len(_SPARK)-1))
        out.append(_SPARK[idx])
    return "".join(out)

def _pct_bar(p: float, width: int=20) -> str:
    p = max(0.0, min(100.0, p))
    filled = int(round((p/100.0)*width))
    return "[" + ("#"*filled) + ("-"*(width-filled)) + f"] {p:0.1f}%"

def _calc_progress(total_sent:int, total_success:int, daily_sent:int, lex_total:int, lex_new:int) -> float:
    qual = 0.0 if total_sent == 0 else min(1.0, (total_success/(total_sent*0.60 + 1e-6)))
    vol  = min(1.0, total_sent/50.0)
    lex  = min(1.0, lex_total/200.0)
    grow = min(1.0, lex_new/15.0)
    return max(0.0, min(100.0, (qual*35 + vol*25 + lex*25 + grow*15)))

async def _find_log_channel(bot: commands.Bot):
    try:
        from ..helpers import log_utils as _lu  # type: ignore
        for attr in ("get_log_channel", "find_log_channel", "get_or_create_log_channel"):
            fn = getattr(_lu, attr, None)
            if callable(fn):
                ch = fn(bot)  # type: ignore
                if ch: return ch
    except Exception:
        pass
    cid = os.getenv("LOG_CHANNEL_ID") or os.getenv("LOG_CHANNEL_ID_RAW") or os.getenv("LOG_CHANNEL")
    if cid:
        try:
            cidn = int(cid)
            for g in bot.guilds:
                ch = g.get_channel(cidn) if hasattr(g, "get_channel") else None
                if ch: return ch
        except Exception:
            pass
    for g in bot.guilds:
        for ch in getattr(g, "text_channels", []):
            return ch
    return None

class LearningProgress(commands.Cog):
    """Maintain 'neuro-lite progress' thread; daily & weekly summaries (Render Free safe)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.thread_id: Optional[int] = None
        self.daily_task.start()
        self.weekly_task.start()

    def cog_unload(self):
        for t in (self.daily_task, self.weekly_task):
            try: t.cancel()
            except Exception: pass

    async def ensure_thread(self):
        ch = await _find_log_channel(self.bot)
        if not ch:
            log.warning("[progress] no log channel found")
            return None
        th = None
        try:
            con = _open_db()
            with con:
                _ensure_meta(con)
                saved = _meta_get(con, "progress_thread_id")
                if saved:
                    tid = int(saved)
                    try:
                        fetched = await self.bot.fetch_channel(tid)
                        if isinstance(fetched, discord.Thread):
                            th = fetched
                    except Exception:
                        th = None
        except Exception:
            th = None
        if th: return th
        try:
            if hasattr(ch, "create_thread"):
                th = await ch.create_thread(name="neuro-lite progress", auto_archive_duration=10080)
            else:
                msg = await ch.send("📈 Progress tracking started.")
                if hasattr(msg, "create_thread"):
                    th = await msg.create_thread(name="neuro-lite progress", auto_archive_duration=10080)
        except Exception as e:
            log.exception("[progress] cannot create thread: %s", e)
            th = None
        if th:
            try:
                con = _open_db()
                with con:
                    _meta_set(con, "progress_thread_id", str(int(th.id)))
            except Exception:
                pass
        return th

    async def _compose_daily(self):
        con = _open_db()
        with con:
            now = _now_ts()
            day = _day_bucket(now)
            total_sent, total_success, per = _read_sticker_stats(con)
            daily_sent = _count_sticker_sent_period(con, day)
            try:
                t, p, n, new_today = _slang_counts(con, since_ts=day)
                lex_total, lex_pos, lex_neg, lex_new = t, p, n, new_today
            except TypeError:
                t, p, n = _slang_counts(con, since_ts=None)
                lex_total, lex_pos, lex_neg, lex_new = t, p, n, 0

            try:
                _upsert_snapshot(con, day, total_sent, total_success, lex_total)
            except Exception:
                pass

            progress = _calc_progress(total_sent, total_success, daily_sent, lex_total, lex_new)
            bar = _pct_bar(progress)

            series = _daily_sent_series(con, days=7)
            spark = _sparkline([c for _,c in series])

            top_emos = sorted(per.items(), key=lambda kv: (kv[1]["success"], kv[1]["sent"]), reverse=True)[:4]
            emos = ", ".join(f"{k}({v['success']}/{v['sent']})" for k,v in top_emos) if top_emos else "—"

            ts = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
            text = (
                f"**Daily Progress — {ts}**\n"
                f"{bar}\n"
                f"- Sticker total: sent={total_sent}, success={total_success}, *today* sent={daily_sent}\n"
                f"- Slang lexicon: total={lex_total} (pos={lex_pos}, neg={lex_neg}), *today* new={lex_new}\n"
                f"- Top emos: {emos}\n"
                f"- 7d sent: {spark}  ({', '.join(str(c) for _,c in series)})\n"
                f"_mode: Render Free • TK–SD learning_"
            )

            try:
                emb = discord.Embed(title="Daily Progress", description=bar, color=0x42b983)
                emb.add_field(name="Stickers",
                              value=f"total sent **{total_sent}**, success **{total_success}**\nToday sent **{daily_sent}**",
                              inline=False)
                emb.add_field(name="Slang",
                              value=f"lexicon **{lex_total}** (pos **{lex_pos}**, neg **{lex_neg}**)\nNew today **{lex_new}**",
                              inline=False)
                emb.add_field(name="Top Emos", value=emos, inline=False)
                emb.add_field(name="7d sent", value=f"`{spark}`", inline=False)
                emb.set_footer(text="Render Free • TK–SD learning")
            except Exception:
                emb = None

        return text, emb

    async def _compose_weekly(self):
        con = _open_db()
        with con:
            day = _day_bucket()
            d_sent, d_succ, d_lex, succ_series = _weekly_deltas_from_snapshots(con, days=7)
            sent_series = _daily_sent_series(con, days=7)
            spark_sent = _sparkline([c for _,c in sent_series])
            spark_succ = _sparkline([c for _,c in succ_series]) if succ_series else "—"
            total_sent, total_success, per = _read_sticker_stats(con)
            t, p, n = _slang_counts(con, since_ts=None)
            ts = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
            text = (
                f"**Weekly Progress — {ts}**\n"
                f"- Δ sent **{d_sent}**, Δ success **{d_succ}**, Δ lexicon **{d_lex}**\n"
                f"- 7d sent: {spark_sent}  ({', '.join(str(c) for _,c in sent_series)})\n"
                f"- 7d success: {spark_succ}\n"
                f"- Totals: sent **{total_sent}**, success **{total_success}**, lexicon **{t}**\n"
                f"_mode: Render Free • TK–SD learning_"
            )
            try:
                emb = discord.Embed(title="Weekly Progress", color=0x5865F2)
                emb.add_field(name="Deltas (7d)",
                              value=f"sent **{d_sent}**, success **{d_succ}**, lexicon **{d_lex}**", inline=False)
                emb.add_field(name="7d sent", value=f"`{spark_sent}`", inline=True)
                emb.add_field(name="7d success", value=f"`{spark_succ}`", inline=True)
                emb.add_field(name="Totals", value=f"sent **{total_sent}**, success **{total_success}**, lexicon **{t}**", inline=False)
                emb.set_footer(text="Render Free • TK–SD learning")
            except Exception:
                emb = None
        return text, emb

    async def post_summary(self):
        th = await self.ensure_thread()
        if not th:
            return False
        text, emb = await self._compose_daily()
        try:
            if emb:
                await th.send(embed=emb)
            else:
                await th.send(text)
            con = _open_db()
            with con:
                _meta_set(con, "progress_last_day", str(_day_bucket()))
            return True
        except Exception:
            log.exception("[progress] failed to post daily")
            return False

    async def post_weekly(self):
        th = await self.ensure_thread()
        if not th:
            return False
        text, emb = await self._compose_weekly()
        try:
            if emb:
                await th.send(embed=emb)
            else:
                await th.send(text)
            con = _open_db()
            with con:
                _meta_set(con, "progress_last_week", str(_day_bucket()))
            return True
        except Exception:
            log.exception("[progress] failed to post weekly")
            return False

    @tasks.loop(minutes=30)
    async def daily_task(self):
        try:
            con = _open_db()
            with con:
                last = _meta_get(con, "progress_last_day")
                today = str(_day_bucket())
                if last == today:
                    return
            if datetime.now().hour < 8:
                return
            await self.post_summary()
        except Exception:
            log.exception("[progress] daily scheduler error")

    @daily_task.before_loop
    async def before_daily(self):
        await self.bot.wait_until_ready()
        try:
            con = _open_db()
            with con:
                last = _meta_get(con, "progress_last_day")
                today = str(_day_bucket())
                if datetime.now().hour >= 8 and last != today:
                    await self.post_summary()
        except Exception:
            pass

    @tasks.loop(hours=2)
    async def weekly_task(self):
        try:
            con = _open_db()
            with con:
                last = _meta_get(con, "progress_last_week")
                now = datetime.now()
                if now.weekday() != 0 or now.hour < 9:
                    return
                today = str(_day_bucket())
                if last == today:
                    return
            await self.post_weekly()
        except Exception:
            log.exception("[progress] weekly scheduler error")

    @weekly_task.before_loop
    async def before_weekly(self):
        await self.bot.wait_until_ready()
async def setup(bot: commands.Bot):
    await bot.add_cog(LearningProgress(bot))


# --- Compat patch: ensure _slang_counts returns 4 values ---
try:
    _orig__slang_counts = _slang_counts
    def _slang_counts(*a, **k):
        res = _orig__slang_counts(*a, **k)
        if isinstance(res, tuple) and len(res) == 3:
            t,p,n = res
            return t,p,n,False
        return res
except Exception:
    pass