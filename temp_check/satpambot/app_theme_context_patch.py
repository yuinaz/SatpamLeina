# app_theme_context_patch.py — drop‑in helper for theme/background/logo context
# How to use in app.py:
#   from app_theme_context_patch import attach_theme_context, register_theme_routes
#   attach_theme_context(app)
#   register_theme_routes(app)
#
# This injects:
#   - theme_path, cache_bust, background_url, bot_logo_url
#   - current_theme, available_themes
# and provides /theme & /settings/theme routes (optional).

import os, sqlite3, time
from pathlib import Path
from flask import session, url_for, request, redirect, render_template, Blueprint

THEME_DIR = Path("static/themes")
DEFAULT_THEME = os.getenv("DEFAULT_THEME", "neo.css")

def _available_themes():
    try:
        if THEME_DIR.exists():
            names = [p.name for p in THEME_DIR.glob("*.css")]
            if names:
                return sorted(names)
    except Exception:
        pass
    # fallback defaults if folder empty
    return ["neo.css", "neon.css"]

def _db_get_setting(key: str):
    try:
        with sqlite3.connect(os.getenv("DB_PATH", "superadmin.db")) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
            row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row[0] if row else None
    except Exception:
        return None

def _db_set_setting(key: str, value: str):
    try:
        with sqlite3.connect(os.getenv("DB_PATH", "superadmin.db")) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
            conn.execute("INSERT INTO settings(key,value) VALUES(?,?) "
                         "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
            conn.commit()
    except Exception:
        pass

def _current_theme_name():
    name = session.get("theme")
    if not name:
        name = _db_get_setting("ui_theme")
    if not name:
        name = os.getenv("THEME")
    themes = set(_available_themes())
    if name in themes:
        return name
    if DEFAULT_THEME in themes:
        return DEFAULT_THEME
    # last resort
    return next(iter(themes), "neo.css")

def _theme_path(name=None):
    if not name:
        name = _current_theme_name()
    return url_for("static", filename=f"themes/{name}")

def _cache_bust_for(file_url: str) -> str:
    # Just use time to keep it simple; or mtime if local file resolvable.
    try:
        # find static file path if possible
        if file_url.startswith("/static/"):
            local = Path(file_url.lstrip("/"))
            if local.exists():
                return str(int(local.stat().st_mtime))
    except Exception:
        pass
    return str(int(time.time()))

def _background_url():
    # priority: ENV -> DB(settings/background_url) -> None
    env_bg = os.getenv("DASH_BACKGROUND_URL")
    if env_bg:
        return env_bg
    db_bg = _db_get_setting("background_url")
    if db_bg:
        return db_bg
    return None

def _bot_logo_url():
    env_logo = os.getenv("BOT_AVATAR_URL")
    if env_logo:
        return env_logo
    db_logo = _db_get_setting("bot_logo_url")
    if db_logo:
        return db_logo
    return "/static/icon-default.png"

def attach_theme_context(app):
    @app.context_processor
    def inject_globals():
        theme = _current_theme_name()
        theme_path = _theme_path(theme)
        return dict(
            current_theme=theme,
            available_themes=_available_themes(),
            theme_path=theme_path,
            cache_bust=_cache_bust_for(theme_path),
            background_url=_background_url(),
            bot_logo_url=_bot_logo_url(),
        )

def register_theme_routes(app):
    bp = Blueprint("theme_bp", __name__)

    @bp.get("/theme")
    def set_theme():
        # support both "name" and "set" param
        name = request.args.get("name") or request.args.get("set") or ""
        if name in _available_themes():
            session["theme"] = name
            _db_set_setting("ui_theme", name)
        ref = request.referrer or "/"
        return redirect(ref)

    @bp.route("/settings/theme", methods=["GET", "POST"])
    def settings_theme():
        if request.method == "POST":
            name = request.form.get("theme") or ""
            if name in _available_themes():
                session["theme"] = name
                _db_set_setting("ui_theme", name)
            return redirect("/settings/theme")
        return render_template("settings_theme.html")

    app.register_blueprint(bp)
