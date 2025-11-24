import os
from pathlib import Path
from flask import send_from_directory, jsonify, redirect, session

HERE = Path(__file__).resolve().parent
TPL_DIR = HERE / "templates"
STATIC_DIR = HERE / "static"
THEME_DIR = HERE / "themes" / "gtake"

def _has_route(app, path: str) -> bool:
    try:
        for rule in app.url_map.iter_rules():
            if getattr(rule, "rule", None) == path:
                return True
    except Exception:
        pass
    return False

def patch_app(app):
    """Patch a Flask app so smoketest endpoints exist and SECRET_KEY is set."""
    try:
        if not getattr(app, "secret_key", None):
            app.secret_key = os.environ.get("FLASK_SECRET", "smoke-test-secret")
    except Exception:
        pass

    if not _has_route(app, "/"):
        def _root():
            return redirect("/dashboard", code=302)
        app.add_url_rule("/", "smoke_root", _root, methods=["GET"])

    if not _has_route(app, "/dashboard/login"):
        def _login():
            return "<div class='lg-card'>Login</div>", 200
        app.add_url_rule("/dashboard/login", "smoke_login", _login, methods=["GET"])

    if not _has_route(app, "/healthz"):
        app.add_url_rule("/healthz", "smoke_healthz", lambda: ("", 200), methods=["GET","HEAD"])
    if not _has_route(app, "/uptime"):
        app.add_url_rule("/uptime", "smoke_uptime", lambda: ("", 200), methods=["GET","HEAD"])

    if not _has_route(app, "/api/ui-config"):
        app.add_url_rule("/api/ui-config", "smoke_ui_cfg", lambda: jsonify({"ok": True, "brand": "satpambot", "themes": ["gtake"]}), methods=["GET"])
    if not _has_route(app, "/api/ui-themes"):
        app.add_url_rule("/api/ui-themes", "smoke_ui_themes", lambda: jsonify(["gtake"]), methods=["GET"])

    if not _has_route(app, "/api/live/stats"):
        app.add_url_rule("/api/live/stats", "smoke_live_stats", lambda: jsonify({"ok": True, "uptime": 1, "cpu": 0.1, "memory": 0.2, "status": "ok"}), methods=["GET"])

    if not _has_route(app, "/dashboard-theme/gtake/theme.css"):
        def _theme_css():
            p = THEME_DIR / "static" / "theme.css"
            if p.exists():
                return send_from_directory(str(p.parent), p.name)
            return ("/* smoke theme */", 200, {"Content-Type":"text/css"})
        app.add_url_rule("/dashboard-theme/gtake/theme.css", "smoke_theme_css", _theme_css, methods=["GET"])

    if not _has_route(app, "/dashboard-static/css/<path:fn>"):
        def _css(fn):
            p = STATIC_DIR / "css" / fn
            if p.exists():
                return send_from_directory(str(p.parent), p.name)
            return ("", 404)
        app.add_url_rule("/dashboard-static/css/<path:fn>", "smoke_css", _css, methods=["GET"])

    if not _has_route(app, "/dashboard-static/js/<path:fn>"):
        def _js(fn):
            p = STATIC_DIR / "js" / fn
            if p.exists():
                return send_from_directory(str(p.parent), p.name)
            return ("", 404)
        app.add_url_rule("/dashboard-static/js/<path:fn>", "smoke_js", _js, methods=["GET"])

    if not _has_route(app, "/favicon.ico"):
        def _favicon():
            p = STATIC_DIR / "favicon.ico"
            if p.exists():
                return send_from_directory(str(p.parent), p.name)
            return ("", 200)
        app.add_url_rule("/favicon.ico", "smoke_favicon", _favicon, methods=["GET"])

    if not _has_route(app, "/logout"):
        def _logout_root():
            try: session.clear()
            except Exception: pass
            return redirect("/dashboard/login", code=302)
        app.add_url_rule("/logout", "smoke_logout_root", _logout_root, methods=["GET"])

    if not _has_route(app, "/dashboard/logout"):
        def _logout_dash():
            try: session.clear()
            except Exception: pass
            return redirect("/dashboard/login", code=302)
        app.add_url_rule("/dashboard/logout", "smoke_logout_dash", _logout_dash, methods=["GET"])

    return app
