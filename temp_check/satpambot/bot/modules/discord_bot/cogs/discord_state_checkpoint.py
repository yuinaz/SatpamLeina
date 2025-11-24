from __future__ import annotations

from discord.ext import commands

import os, io, logging, asyncio, sqlite3, time, hashlib
from typing import Optional
import discord
from discord.ext import tasks

from ..helpers import discord_state_io as dsio

log = logging.getLogger(__name__)

MARKER = "NEUROLITE_CHECKPOINT v1"
ATTACH_NAME = "neuro-lite-state.json.z"

# Anti-spam defaults (can be overridden by env, but not required)
MIN_INTERVAL_HOURS = int(os.getenv("CHECKPOINT_MIN_INTERVAL_HOURS", "12"))
MAX_INTERVAL_HOURS = int(os.getenv("CHECKPOINT_MAX_INTERVAL_HOURS", "36"))
CHANGE_SENT_DELTA    = int(os.getenv("CHECKPOINT_CHANGE_SENT_DELTA", "5"))
CHANGE_SUCCESS_DELTA = int(os.getenv("CHECKPOINT_CHANGE_SUCCESS_DELTA", "2"))
CHANGE_LEX_DELTA     = int(os.getenv("CHECKPOINT_CHANGE_LEX_DELTA", "10"))

def _db_path() -> str:
    return os.getenv("NEUROLITE_MEMORY_DB",
        os.path.join(os.path.dirname(__file__), "..","..","..","..","data","memory.sqlite3"))

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

def _read_core_counters(con: sqlite3.Connection):
    # totals
    sent = succ = 0
    try:
        for r in con.execute("SELECT sent_count, success_count FROM sticker_stats"):
            sent += int(r["sent_count"] or 0)
            succ += int(r["success_count"] or 0)
    except Exception:
        pass
    # lexicon size
    lex = 0
    try:
        cur = con.execute("SELECT COUNT(1) AS c FROM slang_lexicon")
        row = cur.fetchone()
        lex = int(row["c"] or 0) if row else 0
    except Exception:
        pass
    return sent, succ, lex

def _fingerprint_tuple(con: sqlite3.Connection):
    sent, succ, lex = _read_core_counters(con)
    return (sent, succ, lex)

def _should_checkpoint(con: sqlite3.Connection, now_ts: int) -> bool:
    last_ts = int(_meta_get(con, "state_last_ts") or "0")
    last_sent = int(_meta_get(con, "state_last_sent") or "0")
    last_succ = int(_meta_get(con, "state_last_succ") or "0")
    last_lex  = int(_meta_get(con, "state_last_lex")  or "0")

    sent, succ, lex = _fingerprint_tuple(con)
    delta_sent = max(0, sent - last_sent)
    delta_succ = max(0, succ - last_succ)
    delta_lex  = max(0, lex  - last_lex)

    hours = (now_ts - last_ts)/3600 if last_ts else 999

    # Check max interval (force at least once per MAX_INTERVAL_HOURS)
    if hours >= MAX_INTERVAL_HOURS:
        return True

    # Normal case: must pass MIN interval + significant changes
    if hours >= MIN_INTERVAL_HOURS and (
        delta_sent >= CHANGE_SENT_DELTA or
        delta_succ >= CHANGE_SUCCESS_DELTA or
        delta_lex  >= CHANGE_LEX_DELTA
    ):
        return True

    return False

def _remember_checkpoint(con: sqlite3.Connection, now_ts: int):
    sent, succ, lex = _fingerprint_tuple(con)
    _meta_set(con, "state_last_ts", str(int(now_ts)))
    _meta_set(con, "state_last_sent", str(int(sent)))
    _meta_set(con, "state_last_succ", str(int(succ)))
    _meta_set(con, "state_last_lex",  str(int(lex)))

async def _find_log_channel(bot: commands.Bot) -> Optional[discord.TextChannel]:
    # reuse helper if available
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

async def _ensure_progress_thread(bot: commands.Bot) -> Optional[discord.Thread]:
    ch = await _find_log_channel(bot)
    if not ch:
        return None
    # Try saved thread id from meta
    try:
        con = _open_db()
        with con:
            _ensure_meta(con)
            saved = _meta_get(con, "progress_thread_id")
            if saved:
                tid = int(saved)
                try:
                    fetched = await bot.fetch_channel(tid)
                    if isinstance(fetched, discord.Thread):
                        return fetched
                except Exception:
                    pass
    except Exception:
        pass

    # Fall back: search existing threads by name
    try:
        for th in getattr(ch, "threads", []):
            if "progress" in th.name.lower():
                return th
    except Exception:
        pass

    # Create if needed
    try:
        if hasattr(ch, "create_thread"):
            th = await ch.create_thread(name="neuro-lite progress", auto_archive_duration=10080)
            # Save to meta for next time
            try:
                con = _open_db()
                with con:
                    _meta_set(con, "progress_thread_id", str(int(th.id)))
            except Exception:
                pass
            return th
        else:
            msg = await ch.send("📌 Creating neuro-lite progress thread (state).")
            if hasattr(msg, "create_thread"):
                th = await msg.create_thread(name="neuro-lite progress", auto_archive_duration=10080)
                try:
                    con = _open_db()
                    with con:
                        _meta_set(con, "progress_thread_id", str(int(th.id)))
                except Exception:
                    pass
                return th
    except Exception:
        pass
    return None

async def _load_checkpoint_from_pins(th: discord.Thread) -> Optional[bytes]:
    try:
        pins = await th.pins()
        for m in pins:
            if MARKER in (m.content or "") and m.attachments:
                att = m.attachments[0]
                if att.filename.endswith(".z"):
                    data = await att.read()
                    return data
    except Exception:
        log.exception("[state] failed to load pins")
    return None

async def _save_checkpoint_pin(th: discord.Thread, data: bytes) -> bool:
    try:
        # Unpin previous markers (keep timeline clean)
        pins = await th.pins()
        for m in pins:
            if MARKER in (m.content or ""):
                try: await m.unpin()
                except Exception: pass
        # Send new pin
        file = discord.File(io.BytesIO(data), filename=ATTACH_NAME)
        msg = await th.send(content=f"📦 {MARKER}", file=file)
        try: await msg.pin()
        except Exception: pass
        return True
    except Exception:
        log.exception("[state] failed to save pin")
        return False

class DiscordStateCheckpoint(commands.Cog):
    """Persist core learning state into a pinned message attachment in the progress thread.
    Anti-spam: at most once per ~12h unless big changes, forced at 36h.
    Also supports on-demand force via DB meta flag set by scripts/force_checkpoint.py
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sync_task.start()
        self.force_watch_task.start()

    def cog_unload(self):
        for t in (self.sync_task, self.force_watch_task):
            try: t.cancel()
            except Exception: pass

    @tasks.loop(hours=2)
    async def sync_task(self):
        try:
            con = _open_db()
            now_ts = int(time.time())
            with con:
                if not _should_checkpoint(con, now_ts):
                    return
            th = await _ensure_progress_thread(self.bot)
            if not th:
                return
            data = dsio.export_state(limit_tokens=800)
            if await _save_checkpoint_pin(th, data):
                with con:
                    _remember_checkpoint(con, now_ts)
                log.info("[state] checkpoint saved to thread pin (%d bytes)", len(data))
        except Exception:
            log.exception("[state] periodic checkpoint failed")

    @sync_task.before_loop
    async def before_sync(self):
        await self.bot.wait_until_ready()
        # On boot: attempt to restore first
        try:
            th = await _ensure_progress_thread(self.bot)
            if not th:
                return
            data = await _load_checkpoint_from_pins(th)
            if data:
                obj = dsio.import_state(data)
                dsio.apply_state(obj)
                con = _open_db()
                with con:
                    _remember_checkpoint(con, int(time.time()))
                log.info("[state] restored from pinned checkpoint (ts=%s)", obj.get("ts"))
        except Exception:
            log.exception("[state] restore on boot failed")

    @tasks.loop(seconds=90)
    async def force_watch_task(self):
        """Lightweight watcher: if scripts/force_checkpoint.py sets meta flag, do one checkpoint immediately."""
        try:
            con = _open_db()
            now_ts = int(time.time())
            with con:
                flag = _meta_get(con, "force_checkpoint")
                if not flag:
                    return
                # consume flag if not too recent
                try:
                    ts = int(flag)
                except Exception:
                    ts = now_ts
                # Prevent abuse: only honor if older than 30s but newer than 2h
                if now_ts - ts < 30 or now_ts - ts > 7200:
                    _meta_set(con, "force_checkpoint", "")
                    return
                # Clear the flag now to avoid double-run
                _meta_set(con, "force_checkpoint", "")
            th = await _ensure_progress_thread(self.bot)
            if not th:
                return
            data = dsio.export_state(limit_tokens=800)
            if await _save_checkpoint_pin(th, data):
                with con:
                    _remember_checkpoint(con, now_ts)
                log.info("[state] FORCE checkpoint saved to thread pin (%d bytes)", len(data))
        except Exception:
            log.exception("[state] force watcher error")
async def setup(bot: commands.Bot):
    await bot.add_cog(DiscordStateCheckpoint(bot))