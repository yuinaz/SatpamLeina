from __future__ import annotations

import os, time, sqlite3, pathlib
from typing import Optional

def _guess_db_path() -> str:
    # Try ENV first
    envp = os.getenv("ENV_DB_PATH")
    if envp:
        return envp
    # Guess relative to repo root (…/data/runtime_env.db)
    here = pathlib.Path(__file__).resolve()
    cand = here.parents[5] / "data" / "runtime_env.db"
    return str(cand)

def _open_db():
    path = _guess_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS automaton_tickets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kind TEXT,
        module TEXT,
        critical INTEGER DEFAULT 0,
        status TEXT,
        reason TEXT,
        created_ts INTEGER,
        updated_ts INTEGER
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS automaton_state(
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_ts INTEGER
    )""")
    con.commit()
    return con

def create_ticket(kind: str, module: str, reason: str, critical: bool=False) -> int:
    now = int(time.time())
    con = _open_db()
    try:
        cur = con.execute("""INSERT INTO automaton_tickets(kind,module,critical,status,reason,created_ts,updated_ts)
                             VALUES(?,?,?,?,?,?,?)""",
                             (kind, module, 1 if critical else 0, "pending", reason, now, now))
        con.commit()
        return int(cur.lastrowid)
    finally:
        con.close()

def update_ticket_status(ticket_id: int, status: str):
    con = _open_db()
    try:
        con.execute("UPDATE automaton_tickets SET status=?, updated_ts=? WHERE id=?",
                    (status, int(time.time()), int(ticket_id)))
        con.commit()
    finally:
        con.close()

def get_ticket(ticket_id: int):
    con = _open_db()
    try:
        row = con.execute("SELECT * FROM automaton_tickets WHERE id=?", (int(ticket_id),)).fetchone()
        return dict(row) if row else None
    finally:
        con.close()

def latest_pending():
    con = _open_db()
    try:
        row = con.execute("SELECT * FROM automaton_tickets WHERE status='pending' ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None
    finally:
        con.close()

def list_pending(limit: int=10):
    con = _open_db()
    try:
        rows = con.execute("SELECT * FROM automaton_tickets WHERE status='pending' ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()

def state_get(key: str, default: str="") -> str:
    con = _open_db()
    try:
        row = con.execute("SELECT value FROM automaton_state WHERE key=?", (key,)).fetchone()
        if row: return str(row["value"])
    finally:
        con.close()
    return default

def state_set(key: str, value: str):
    con = _open_db()
    try:
        con.execute("""INSERT INTO automaton_state(key,value,updated_ts)
                       VALUES(?,?,?)
                       ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_ts=excluded.updated_ts""",
                    (key, value, int(time.time())))
        con.commit()
    finally:
        con.close()
