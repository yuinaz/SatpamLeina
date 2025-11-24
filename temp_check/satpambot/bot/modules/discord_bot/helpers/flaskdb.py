import os, sqlite3, time

DB_PATH = os.getenv("DB_PATH", "superadmin.db")

def ensure_schema():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS banned_users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                username TEXT,
                guild_id TEXT,
                reason TEXT,
                banned_at TEXT,
                active INTEGER DEFAULT 1,
                unbanned_at TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS bot_guilds(
                id TEXT PRIMARY KEY,
                name TEXT,
                icon_url TEXT
            )"""
        )
        conn.commit()

def insert_ban(user_id: str, username: str, guild_id: str, reason: str = ""):
    ensure_schema()
    now = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO banned_users (user_id, username, guild_id, reason, banned_at, active)
                 VALUES (?,?,?,?,?,1)""",
            (str(user_id), username or "-", str(guild_id), reason or "", now)
        )
        conn.commit()

def mark_unban(user_id: str, guild_id: str):
    ensure_schema()
    now = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """UPDATE banned_users SET active=0, unbanned_at=?
                 WHERE user_id=? AND guild_id=? AND active=1""" ,
            (now, str(user_id), str(guild_id))
        )
        conn.commit()

def compute_stats(guild_id: str | int | None = None):
    ensure_schema()
    gid = str(guild_id) if guild_id else None
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if gid:
            total_bans = conn.execute("SELECT COUNT(1) FROM banned_users WHERE guild_id=?", (gid,)).fetchone()[0]
        else:
            total_bans = conn.execute("SELECT COUNT(1) FROM banned_users").fetchone()[0]
        days, vals = [], []
        now = int(time.time())
        for i in range(6, -1, -1):
            d0 = now - i*86400
            d1s = time.strftime('%Y-%m-%d 00:00:00', time.localtime(d0))
            d2s = time.strftime('%Y-%m-%d 23:59:59', time.localtime(d0))
            if gid:
                c = conn.execute("SELECT COUNT(1) FROM banned_users WHERE guild_id=? AND banned_at BETWEEN ? AND ?", (gid, d1s, d2s)).fetchone()[0]
            else:
                c = conn.execute("SELECT COUNT(1) FROM banned_users WHERE banned_at BETWEEN ? AND ?", (d1s, d2s)).fetchone()[0]
            days.append(time.strftime('%a', time.localtime(d0)))
            vals.append(c)
        guilds = conn.execute(
            """SELECT g.id, g.name, g.icon_url, COALESCE(COUNT(b.id),0) AS detections
                 FROM bot_guilds g
                 LEFT JOIN banned_users b ON b.guild_id = g.id
                 GROUP BY g.id, g.name, g.icon_url
                 ORDER BY detections DESC, LOWER(g.name) ASC
                 LIMIT 5"""
        ).fetchall()
        if gid:
            bans = conn.execute("SELECT username, user_id, guild_id, reason, banned_at FROM banned_users WHERE guild_id=? ORDER BY banned_at DESC LIMIT 8", (gid,)).fetchall()
        else:
            bans = conn.execute("SELECT username, user_id, guild_id, reason, banned_at FROM banned_users ORDER BY banned_at DESC LIMIT 8").fetchall()
    return {
        "core_total": total_bans,
        "barLeft": {"labels": days, "values": vals},
        "topGuilds": [dict(x) for x in guilds],
        "bans": [dict(x) for x in bans],
    }
