import os, sqlite3, time
DEFAULT_DB = os.getenv("NEUROLITE_MEMORY_DB",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "memory.sqlite3"))

def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

class UpgradeStore:
    def __init__(self, db_path: str = DEFAULT_DB):
        self.db_path = os.path.abspath(db_path)
        _ensure_dir(self.db_path); self._init()

    def _init(self):
        con = sqlite3.connect(self.db_path)
        try:
            con.execute("""CREATE TABLE IF NOT EXISTS upgrades(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                channel_id INTEGER,
                msg_id INTEGER,
                module TEXT,
                reason TEXT,
                status TEXT,
                ts INTEGER
            )""")
            con.commit()
        finally:
            con.close()

    def create(self, user_id: int, guild_id: int, channel_id: int, msg_id: int, module: str, reason: str) -> int:
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.cursor()
            cur.execute("INSERT INTO upgrades(user_id,guild_id,channel_id,msg_id,module,reason,status,ts) VALUES (?,?,?,?,?,?,?,?)",
                        (int(user_id), int(guild_id), int(channel_id), int(msg_id), module, reason, "pending", int(time.time())))
            con.commit()
            return int(cur.lastrowid or 0)
        finally:
            con.close()

    def latest_pending(self):
        con = sqlite3.connect(self.db_path); con.row_factory = sqlite3.Row
        try:
            cur = con.cursor()
            cur.execute("SELECT * FROM upgrades WHERE status='pending' ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            con.close()

    def set_status(self, upg_id: int, status: str):
        con = sqlite3.connect(self.db_path)
        try:
            con.execute("UPDATE upgrades SET status=? WHERE id=?", (status, int(upg_id)))
            con.commit()
        finally:
            con.close()
