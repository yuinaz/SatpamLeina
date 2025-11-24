import os
from pathlib import Path
from flask import Flask, redirect, render_template, send_from_directory, jsonify, session

HERE = Path(__file__).resolve().parent
TPL_DIR = HERE / "templates"
STATIC_DIR = HERE / "static"
THEME_DIR = HERE / "themes" / "gtake"

def create_app(testing: bool = True):
    app = Flask(
        __name__,
        template_folder=str(TPL_DIR),
        static_folder=str(STATIC_DIR),
        static_url_path="/dashboard-static",
    )
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET", "smoke-test-secret")
    app.config["TESTING"] = testing

    @app.route("/")
    def root():
        return redirect("/dashboard", code=302)

    @app.route("/dashboard")
    def dash():
        return redirect("/dashboard/login", code=302)

    @app.route("/dashboard/login")
    def login():
        tpl = TPL_DIR / "login.html"
        if tpl.exists():
            try:
                return render_template("login.html")
            except Exception:
                pass
        return "<div class='lg-card'>Login</div>", 200

    @app.route("/healthz", methods=["GET", "HEAD"])
    def healthz():
        return ("", 200)

    @app.route("/uptime", methods=["GET", "HEAD"])
    def uptime():
        return ("", 200)

    @app.route("/api/ui-config")
    def ui_cfg():
        return jsonify({"ok": True, "brand": "satpambot", "themes": ["gtake"]})

    @app.route("/api/ui-themes")
    def ui_themes():
        return jsonify(["gtake"])

    @app.route("/dashboard-theme/gtake/theme.css")
    def theme_css():
        p = THEME_DIR / "static" / "theme.css"
        if p.exists():
            return send_from_directory(str(p.parent), p.name)
        return ("/* smoke theme */", 200, {"Content-Type":"text/css"})

    @app.route("/api/live/stats")
    def live_stats():
        return jsonify({"ok": True, "uptime": 1, "cpu": 0.1, "memory": 0.2, "status": "ok"})

    @app.route("/api/phish/phash")
    def phash():
        return ("", 404)

    @app.route("/logout")
    def logout_root():
        try: session.clear()
        except Exception: pass
        return redirect("/dashboard/login", code=302)

    @app.route("/dashboard/logout")
    def logout_dash():
        try: session.clear()
        except Exception: pass
        return redirect("/dashboard/login", code=302)

    @app.route("/favicon.ico")
    def favicon():
        p = STATIC_DIR / "favicon.ico"
        if p.exists():
            return send_from_directory(str(p.parent), p.name)
        return ("", 200)

    return app
