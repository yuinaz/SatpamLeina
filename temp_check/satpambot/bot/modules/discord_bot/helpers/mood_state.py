from __future__ import annotations

import os, sqlite3, time
from typing import Optional

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

def meta_get(con: sqlite3.Connection, key: str) -> Optional[str]:
    _ensure_meta(con)
    row = con.execute("SELECT value FROM learning_progress_meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None

def meta_set(con: sqlite3.Connection, key: str, val: str):
    _ensure_meta(con)
    con.execute("INSERT INTO learning_progress_meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, val))
    con.commit()

def bump_learning(con: Optional[sqlite3.Connection]=None):
    own = False
    if con is None:
        con = _open_db(); own = True
    try:
        meta_set(con, "last_learning_ts", str(int(time.time())))
        # optional: set focus mood
        meta_set(con, "mood", "focused")
    finally:
        if own: con.close()

def set_mood(mood: str, con: Optional[sqlite3.Connection]=None):
    own = False
    if con is None:
        con = _open_db(); own = True
    try:
        meta_set(con, "mood", mood)
        meta_set(con, "mood_ts", str(int(time.time())))
    finally:
        if own: con.close()

def get_mood(con: Optional[sqlite3.Connection]=None) -> str:
    own = False
    if con is None:
        con = _open_db(); own = True
    try:
        m = meta_get(con, "mood") or "neutral"
        ts = int(meta_get(con, "mood_ts") or "0")
        if ts and time.time() - ts > 600 and m != "neutral":
            # decay after 10m
            return "neutral"
        return m
    finally:
        if own: con.close()

def is_learning_active(window_sec: int=180, con: Optional[sqlite3.Connection]=None) -> bool:
    own = False
    if con is None:
        con = _open_db(); own = True
    try:
        ts = int(meta_get(con, "last_learning_ts") or "0")
        return (time.time() - ts) < window_sec if ts else False
    finally:
        if own: con.close()

def counters(con: sqlite3.Connection):
    sent = succ = 0
    try:
        for r in con.execute("SELECT sent_count, success_count FROM sticker_stats"):
            sent += int(r["sent_count"] or 0)
            succ += int(r["success_count"] or 0)
    except Exception:
        pass
    lex = 0
    try:
        row = con.execute("SELECT COUNT(1) AS c FROM slang_lexicon").fetchone()
        if row: lex = int(row["c"] or 0)
    except Exception:
        pass
    return sent, succ, lex

def update_from_counters(con: sqlite3.Connection, sent: int, succ: int, lex: int) -> bool:
    """Store counters and return True if there's fresh learning activity."""
    ls = int(meta_get(con, "counters_sent") or "0")
    ll = int(meta_get(con, "counters_lex") or "0")
    activity = (sent - ls >= 3) or (lex - ll >= 2)  # thresholds
    meta_set(con, "counters_sent", str(sent))
    meta_set(con, "counters_lex", str(lex))
    if activity:
        bump_learning(con)
    return activity
