from __future__ import annotations

import os, sqlite3, time
from dataclasses import dataclass
from typing import Optional, List

DB_PATH = os.environ.get("NEURO_DB", "data/neuro_memory.sqlite3")

@dataclass
class MemoryItem:
    id: int; guild_id: int; channel_id: int; user_id: int; content: str; tags: str; score: float

class MemoryStore:
    def __init__(self, path: str = DB_PATH):
        d = os.path.dirname(path) or "."
        os.makedirs(d, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        c = self.conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS mem (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER, channel_id INTEGER, user_id INTEGER,
            content TEXT NOT NULL, tags TEXT DEFAULT '',
            created_ts REAL, updated_ts REAL, weight REAL DEFAULT 1.0
        )""")
        try:
            c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS mem_fts USING fts5(content, tags, content='mem', content_rowid='id')")
            c.execute("CREATE TRIGGER IF NOT EXISTS mem_ai AFTER INSERT ON mem BEGIN INSERT INTO mem_fts(rowid, content, tags) VALUES (new.id, new.content, new.tags); END;")
            c.execute("CREATE TRIGGER IF NOT EXISTS mem_ad AFTER DELETE ON mem BEGIN INSERT INTO mem_fts(mem_fts, rowid, content, tags) VALUES('delete', old.id, old.content, old.tags); END;")
            c.execute("CREATE TRIGGER IF NOT EXISTS mem_au AFTER UPDATE ON mem BEGIN INSERT INTO mem_fts(mem_fts, rowid, content, tags) VALUES('delete', old.id, old.content, old.tags); INSERT INTO mem_fts(rowid, content, tags) VALUES (new.id, new.content, new.tags); END;")
            self.has_fts = True
        except sqlite3.OperationalError:
            self.has_fts = False
        self.conn.commit()

    def upsert(self, guild_id: int, channel_id: int, user_id: int, content: str, tags: str = "") -> int:
        now = time.time()
        cur = self.conn.cursor()
        cur.execute("INSERT INTO mem (guild_id, channel_id, user_id, content, tags, created_ts, updated_ts) VALUES (?,?,?,?,?,?,?)",
                    (guild_id, channel_id, user_id, content, tags, now, now))
        self.conn.commit()
        return int(cur.lastrowid)