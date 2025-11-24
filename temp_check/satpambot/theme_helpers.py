import os, json, sqlite3, time
from pathlib import Path as _Path
from flask import session, url_for

THEME_DIR = _Path("static/themes")
DEFAULT_THEME = os.getenv("DEFAULT_THEME", "neo.css")

def _available_themes():
    try:
        return sorted([p.name for p in THEME_DIR.glob("*.css")])
    except Exception:
        return ["neo.css", "neon.css"]

def _theme_exists(name: str) -> bool:
    if not name:
        return False
    fn = name if name.endswith('.css') else (name + '.css')
    return (THEME_DIR / fn).exists()

def _current_theme_name():
    name = session.get("theme")
    if not name:
        try:
            with sqlite3.connect(os.getenv("DB_PATH", "superadmin.db")) as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
                row = conn.execute("SELECT value FROM settings WHERE key='ui_theme'").fetchone()
                if row and row[0]:
                    name = row[0]
        except Exception:
            pass
    if not name:
        name = os.getenv("THEME") or DEFAULT_THEME
    if not name.endswith('.css'):
        name += '.css'
    if _theme_exists(name):
        return name
    avail = _available_themes()
    return avail[0] if avail else 'neo.css'

def get_theme_path():
    fn = _current_theme_name()
    return url_for('static', filename=f'themes/{fn}')

def _load_background_url():
    # 1) config/theme.json
    try:
        cfg = json.load(open('config/theme.json','r',encoding='utf-8'))
        url = (cfg.get('background_image') or '').strip()
        if url:
            return url if url.startswith(('http://','https://','/')) else ('/' + url.lstrip())
    except Exception:
        pass
    # 2) SQLite assets -> /assets/background
    try:
        with sqlite3.connect(os.getenv('DB_PATH', 'superadmin.db')) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS assets(key TEXT PRIMARY KEY, mime TEXT, data BLOB, updated_at TEXT)")
            if conn.execute("SELECT 1 FROM assets WHERE key='background'").fetchone():
                return '/assets/background'
    except Exception:
        pass
    return ''
