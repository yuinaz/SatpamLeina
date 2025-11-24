import os, sqlite3, time, random
from typing import Dict, Any, Optional

DEFAULT_DB = os.getenv("NEUROLITE_MEMORY_DB",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "memory.sqlite3"))

def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

class StickerLearner:
    def __init__(self, db_path: str = DEFAULT_DB):
        self.db_path = os.path.abspath(db_path)
        _ensure_dir(self.db_path)
        self._init_db()

    def _init_db(self):
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS sticker_events (
                user_id INTEGER,
                ts INTEGER,
                emotion TEXT,
                used INTEGER,
                success INTEGER,
                guild_id INTEGER,
                dm INTEGER,
                has_user_sticker INTEGER,
                exclam INTEGER,
                laugh_www INTEGER,
                laugh_wkwk INTEGER,
                laugh_lol INTEGER
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS sticker_stats (
                emotion TEXT PRIMARY KEY,
                sent_count INTEGER,
                success_count INTEGER
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS sticker_catalog (
                sticker_id INTEGER PRIMARY KEY,
                name TEXT,
                guild_id INTEGER
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS sticker_sent (
                msg_id INTEGER PRIMARY KEY,
                sticker_id INTEGER,
                guild_id INTEGER,
                channel_id INTEGER,
                emotion TEXT,
                ts INTEGER
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS sticker_feedback (
                msg_id INTEGER PRIMARY KEY,
                pos INTEGER DEFAULT 0,
                neg INTEGER DEFAULT 0,
                credited INTEGER DEFAULT 0
            )""")
            con.commit()
        finally:
            con.close()

    # Catalog
    def update_catalog_from_bot(self, bot):
        items = []
        for g in getattr(bot, "guilds", []):
            try:
                try:
                    stickers = (bot.loop.run_until_complete(g.fetch_stickers()))
                except Exception:
                    stickers = getattr(g, "stickers", []) or []
                for s in stickers:
                    items.append((int(getattr(s, "id", 0)), str(getattr(s, "name", "")), int(getattr(g, "id", 0))))
            except Exception:
                continue
        if not items: return 0
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.cursor()
            for sid, name, gid in items:
                cur.execute("INSERT OR REPLACE INTO sticker_catalog(sticker_id, name, guild_id) VALUES (?,?,?)",
                            (sid, name, gid))
            con.commit()
        finally:
            con.close()
        return len(items)

    # Recommendation
    def recommend_rate(self, base_rate: float, style_summary: Dict[str,int], has_user_sticker: bool,
                       emotion: str, min_rate: float, max_rate: float) -> float:
        rate = float(base_rate)
        if has_user_sticker:
            rate += float(os.getenv("STICKER_BOOST_USER_STICKER", 0.20))
        if (style_summary.get("exclam", 0) or 0) >= 2:
            rate += float(os.getenv("STICKER_BOOST_EXCLAM", 0.10))
        laugh_sum = (style_summary.get("www",0) or 0) + (style_summary.get("wkwk",0) or 0) + (style_summary.get("lol",0) or 0)
        if laugh_sum >= 1:
            rate += float(os.getenv("STICKER_BOOST_LAUGH", 0.10))
        con = sqlite3.connect(self.db_path); con.row_factory = sqlite3.Row
        try:
            cur = con.cursor()
            cur.execute("SELECT sent_count, success_count FROM sticker_stats WHERE emotion=?", (emotion,))
            row = cur.fetchone()
            if row and (row["sent_count"] or 0) > 5:
                succ = (row["success_count"] or 0) / max(1, row["sent_count"])
                rate = 0.6*rate + 0.4*succ
        finally:
            con.close()
        rate = max(min_rate, min(max_rate, rate))
        return rate

    def pick_sticker(self, bot, guild_id: int | None, emotion: str):
        con = sqlite3.connect(self.db_path); con.row_factory = sqlite3.Row
        try:
            cur = con.cursor()
            if guild_id:
                cur.execute("SELECT sticker_id FROM sticker_catalog WHERE guild_id=?", (int(guild_id),))
                rows = [r["sticker_id"] for r in cur.fetchall()]
                if rows: return int(random.choice(rows))
            cur.execute("SELECT sticker_id FROM sticker_catalog")
            rows = [r["sticker_id"] for r in cur.fetchall()]
            if rows: return int(random.choice(rows))
        finally:
            con.close()
        return None

    # Logging
    def log_event(self, user_id: int, emotion: str, used: bool, success: bool,
                  guild_id: int | None, dm: bool, has_user_sticker: bool, style_summary: Dict[str,int]):
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.cursor()
            cur.execute("""INSERT INTO sticker_events
                (user_id, ts, emotion, used, success, guild_id, dm, has_user_sticker, exclam, laugh_www, laugh_wkwk, laugh_lol)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (
                    int(user_id), int(time.time()), str(emotion or "neutral"), int(bool(used)), int(bool(success)),
                    int(guild_id or 0), int(bool(dm)), int(bool(has_user_sticker)),
                    int(style_summary.get("exclam",0) or 0),
                    int(style_summary.get("www",0) or 0),
                    int(style_summary.get("wkwk",0) or 0),
                    int(style_summary.get("lol",0) or 0),
                ))
            if used:
                cur.execute("""INSERT INTO sticker_stats(emotion, sent_count, success_count)
                               VALUES (?,1,?)
                               ON CONFLICT(emotion) DO UPDATE SET
                               sent_count=sent_count+1,
                               success_count=success_count+excluded.success_count""",
                            (str(emotion or "neutral"), int(bool(success))))
            con.commit()
        finally:
            con.close()

    # Message mapping & feedback
    def record_sent_message(self, msg_id: int, sticker_id: int, guild_id: int | None, channel_id: int | None, emotion: str):
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.cursor()
            cur.execute("""INSERT OR REPLACE INTO sticker_sent(msg_id, sticker_id, guild_id, channel_id, emotion, ts)
                           VALUES (?,?,?,?,?,?)""", (int(msg_id), int(sticker_id), int(guild_id or 0), int(channel_id or 0), emotion, int(time.time())))
            cur.execute("INSERT OR IGNORE INTO sticker_feedback(msg_id, pos, neg, credited) VALUES (?,0,0,0)", (int(msg_id),))
            con.commit()
        finally:
            con.close()

    def get_sent_emotion(self, msg_id: int) -> Optional[str]:
        con = sqlite3.connect(self.db_path); con.row_factory = sqlite3.Row
        try:
            cur = con.cursor()
            cur.execute("SELECT emotion FROM sticker_sent WHERE msg_id=?", (int(msg_id),))
            row = cur.fetchone()
            return row["emotion"] if row else None
        finally:
            con.close()

    def record_reaction(self, msg_id: int, is_positive: bool, delta: int = 1):
        delta = int(delta)
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.cursor()
            if is_positive:
                cur.execute("UPDATE sticker_feedback SET pos = MAX(0, pos + ?) WHERE msg_id=?", (delta, int(msg_id)))
            else:
                cur.execute("UPDATE sticker_feedback SET neg = MAX(0, neg + ?) WHERE msg_id=?", (delta, int(msg_id)))
            if cur.rowcount == 0:
                cur.execute("INSERT OR IGNORE INTO sticker_feedback(msg_id, pos, neg, credited) VALUES (?, ?, ?, 0)",
                            (int(msg_id), max(0,delta) if is_positive else 0, 0 if is_positive else max(0,delta)))
            con.commit()
        finally:
            con.close()

    def maybe_credit_success_from_feedback(self, msg_id: int, pos_threshold: int, neg_threshold: int) -> bool:
        con = sqlite3.connect(self.db_path); con.row_factory = sqlite3.Row
        credited = False
        try:
            cur = con.cursor()
            cur.execute("SELECT pos, neg, credited FROM sticker_feedback WHERE msg_id=?", (int(msg_id),))
            row = cur.fetchone()
            if not row: return False
            pos, neg, done = int(row["pos"]), int(row["neg"]), int(row["credited"])
            if done: return False
            if pos >= int(pos_threshold) and neg < int(neg_threshold):
                cur.execute("SELECT emotion FROM sticker_sent WHERE msg_id=?", (int(msg_id),))
                r2 = cur.fetchone()
                emo = (r2["emotion"] if r2 else "neutral")
                cur.execute("""INSERT INTO sticker_stats(emotion, sent_count, success_count)
                               VALUES (?,0,1)
                               ON CONFLICT(emotion) DO UPDATE SET
                               success_count=success_count+1""",
                            (str(emo),))
                cur.execute("UPDATE sticker_feedback SET credited=1 WHERE msg_id=?", (int(msg_id),))
                con.commit()
                credited = True
        finally:
            con.close()
        return credited
