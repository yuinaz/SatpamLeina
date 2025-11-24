import sqlite3
from contextlib import contextmanager

def _apply_pragmas(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("PRAGMA page_size=4096;")
    cur.execute("PRAGMA cache_size=20000;")
    cur.execute("PRAGMA temp_store=MEMORY;")
    cur.execute("PRAGMA foreign_keys=ON;")
    cur.execute("PRAGMA wal_autocheckpoint=1000;")
    cur.close()

def open_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    _apply_pragmas(conn)
    return conn

@contextmanager
def db(path: str):
    conn = open_db(path)
    try:
        yield conn
    finally:
        conn.close()
