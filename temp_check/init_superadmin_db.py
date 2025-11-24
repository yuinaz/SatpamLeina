
import os
import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = "superadmin.db"

def init_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS superadmin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            ts TEXT,
            action TEXT
        )
    """)

def main():
    user = os.getenv("SUPER_ADMIN_USER") or "admin"
    passwd = os.getenv("SUPER_ADMIN_PASS") or os.getenv("ADMIN_PASSWORD")
    if not passwd:
        raise SystemExit("SUPER_ADMIN_PASS/ADMIN_PASSWORD harus di-set di ENV.")

    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        init_tables(conn)
        cur = conn.execute("SELECT id FROM superadmin WHERE username=?", (user,))
        if cur.fetchone():
            conn.execute("UPDATE superadmin SET password=? WHERE username=?", (generate_password_hash(passwd), user))
            conn.execute("INSERT INTO admin_history(username, ts, action) VALUES (?, datetime('now'), ?)",
                         (user, "update_password_from_env"))
            print(f"Updated admin '{user}' from ENV.")
        else:
            conn.execute("INSERT INTO superadmin(username, password) VALUES (?, ?)",
                         (user, generate_password_hash(passwd)))
            conn.execute("INSERT INTO admin_history(username, ts, action) VALUES (?, datetime('now'), ?)",
                         (user, "create_from_env"))
            print(f"Created admin '{user}' from ENV.")

if __name__ == '__main__':
    main()
