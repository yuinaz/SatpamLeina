import sqlite3, os

DEFAULT_DB = os.getenv("NEUROLITE_MEMORY_DB",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "memory.sqlite3"))

def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

class EmojiCatalog:
    def __init__(self, db_path: str = DEFAULT_DB):
        self.db_path = os.path.abspath(db_path)
        _ensure_dir(self.db_path)
        self._init_db()

    def _init_db(self):
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS emoji_catalog(
                id INTEGER PRIMARY KEY,
                name TEXT,
                guild_id INTEGER
            )""")
            con.commit()
        finally:
            con.close()

    def sync_from_guilds(self, bot):
        rows = []
        for g in getattr(bot, "guilds", []):
            try:
                for e in getattr(g, "emojis", []) or []:
                    rows.append((int(getattr(e,"id",0)), str(getattr(e,"name","")).lower(), int(getattr(g,"id",0))))
            except Exception:
                continue
        if not rows: return 0
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.cursor()
            for eid, name, gid in rows:
                cur.execute("INSERT OR REPLACE INTO emoji_catalog(id,name,guild_id) VALUES (?,?,?)", (eid,name,gid))
            con.commit()
        finally:
            con.close()
        return len(rows)
