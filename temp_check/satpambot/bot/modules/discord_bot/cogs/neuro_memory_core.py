from __future__ import annotations

from discord.ext import commands
import os, sqlite3, time, logging
from dataclasses import dataclass
from typing import Optional, List
import discord

log = logging.getLogger(__name__)
DB_PATH = os.environ.get("NEURO_DB", "data/neuro_memory.sqlite3")
TOP_K_DEFAULT = int(os.environ.get("NEURO_TOPK", "5"))
PROMOTE_WEIGHT = 2.0

@dataclass
class MemoryItem:
    id: int
    guild_id: int
    channel_id: int
    user_id: int
    content: str
    tags: str
    score: float

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

    def promote(self, mem_id: int, factor: float = PROMOTE_WEIGHT):
        self.conn.execute("UPDATE mem SET weight = weight + ?, updated_ts = ? WHERE id = ?", (factor, time.time(), mem_id))
        self.conn.commit()

    def delete(self, mem_id: int):
        self.conn.execute("DELETE FROM mem WHERE id = ?", (mem_id,))
        self.conn.commit()

    def search(self, guild_id: int, channel_id: Optional[int], query: str, top_k: int = TOP_K_DEFAULT) -> List[MemoryItem]:
        q = (query or "").strip()
        if not q:
            rows = self.conn.execute("SELECT * FROM mem WHERE guild_id=? ORDER BY updated_ts DESC LIMIT ?", (guild_id, top_k)).fetchall()
            return [MemoryItem(r["id"], r["guild_id"], r["channel_id"], r["user_id"], r["content"], r["tags"] or "", float(r["weight"])) for r in rows]
        if getattr(self, "has_fts", False):
            rows = self.conn.execute(
                """SELECT m.*, 
                          (CASE WHEN m.channel_id=? THEN 1.15 ELSE 1.0 END) * m.weight 
                          * (1.0 + 0.000001*(strftime('%s','now') - m.updated_ts)) AS s
                   FROM mem m JOIN mem_fts f ON m.id=f.rowid
                   WHERE m.guild_id=? AND mem_fts MATCH ?
                   ORDER BY s DESC LIMIT ?""",
                (channel_id or 0, guild_id, q, top_k),
            ).fetchall()
            return [MemoryItem(r["id"], r["guild_id"], r["channel_id"], r["user_id"], r["content"], r["tags"] or "", float(r["s"])) for r in rows]
        else:
            rows = self.conn.execute(
                """SELECT *,(CASE WHEN channel_id=? THEN 1.15 ELSE 1.0 END)*weight AS s
                   FROM mem 
                   WHERE guild_id=? AND (content LIKE ? OR tags LIKE ?)
                   ORDER BY s DESC, updated_ts DESC LIMIT ?""",
                (channel_id or 0, guild_id, f"%{q}%", f"%{q}%", top_k),
            ).fetchall()
            return [MemoryItem(r["id"], r["guild_id"], r["channel_id"], r["user_id"], r["content"], r["tags"] or "", float(r["s"])) for r in rows]
async def setup(bot: commands.Bot):
    setattr(bot, "_neuro_db", MemoryStore())