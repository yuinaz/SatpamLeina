import sqlite3, os, time
from typing import Optional

DEFAULT_DB = os.getenv("NEUROLITE_MEMORY_DB",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "memory.sqlite3"))

def sticker_get_recent_in_channel(channel_id: int, window_sec: int) -> Optional[tuple[int, str, int]]:
    con = sqlite3.connect(DEFAULT_DB); con.row_factory = sqlite3.Row
    try:
        cur = con.cursor()
        cur.execute("SELECT msg_id, emotion, ts FROM sticker_sent WHERE channel_id=? ORDER BY ts DESC LIMIT 1", (int(channel_id),))
        row = cur.fetchone()
        if not row: return None
        if int(time.time()) - int(row["ts"]) <= int(window_sec):
            return (int(row["msg_id"]), str(row["emotion"]), int(row["ts"]))
        return None
    finally:
        con.close()
