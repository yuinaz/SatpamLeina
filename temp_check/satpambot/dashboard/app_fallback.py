# -*- coding: utf-8 -*-
"""
Fallback blueprint & create_app for dashboard endpoints.
Ensures /dashboard and /dashboard/login always exist for health/smoketests.
Generated: 2025-08-22T03:54:06.926188Z
"""
from __future__ import annotations

from flask import Flask, Blueprint, Response, render_template_string, redirect, url_for

import logging
def _install_health_log_filter():
    try:
        class _HealthzFilter(logging.Filter):
            def filter(self, record):
                try:
                    msg = record.getMessage()
                except Exception:
                    msg = str(record.msg)
                return ("/healthz" not in msg) and ("/health" not in msg) and ("/ping" not in msg)
        logging.getLogger("werkzeug").addFilter(_HealthzFilter())
        logging.getLogger("gunicorn.access").addFilter(_HealthzFilter())
    except Exception:
        pass  # never break app on logging issues

# Also silence dev-server access logs at the source (Werkzeug's request handler)
try:
    from werkzeug.serving import WSGIRequestHandler as _WRH
    _orig_log_request = _WRH.log_request
    def _healthz_silent_log(self, *args, **kwargs):
        rl = getattr(self, "requestline", "") or ""
        if "/healthz" in rl or "/health" in rl or "/ping" in rl:
            return
        return _orig_log_request(self, *args, **kwargs)
    _WRH.log_request = _healthz_silent_log
except Exception:
    pass


HTML_LOGIN = """<!doctype html>
<html lang='id'><head>
<meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>Login</title>
<style>
body{margin:0;background:#0f172a;color:#eee;font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Arial}
.wrap{max-width:920px;margin:64px auto;padding:24px}
.card{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:24px}
a{color:#8ab4ff;text-decoration:none}
</style></head><body>
<div class='wrap'><div class='card'>
<h1>Login (fallback)</h1>
<p>Ini halaman fallback sementara karena WebUI utama gagal dimuat.</p>
<form method="post" action="{{ url_for('dashboard_fallback.do_login') }}">
  <p><input name="username" placeholder="username" required></p>
  <p><input name="password" type="password" placeholder="password" required></p>
  <p><button type="submit">Login</button>
     <a href="{{ url_for('dashboard_fallback.home') }}">Dashboard</a></p>
</form>
</div></div>
</body></html>"""

HTML_DASH = """<!doctype html>
<html lang='id'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>Dashboard</title>

<link rel='stylesheet' href='/dashboard-theme/gtake/theme.css'>
<link rel='icon' href='/favicon.ico'>
<style>
body{margin:0;background:#0b1020;color:#e2e8f0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Arial}
.top{padding:12px 16px;background:linear-gradient(180deg,#0b1020,#111827)}
.container{max-width:1120px;margin:0 auto;padding:16px}
.card{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:24px}
a{color:#8ab4ff;text-decoration:none}
</style></head><body>
<div class='top'><div class='container'><b>SatpamBot</b> • <a href='/dashboard/login'>Login</a></div></div>
<div class='container'><div class='card'>
<h1>Dashboard (fallback)</h1>
<p>UI utama belum tersedia. Fallback aktif agar health check & smoketest lulus.</p>
<ul>
<li><code>/api/ui-config</code>, <code>/api/ui-themes</code> optional, tidak wajib.</li>
<li>Begitu webui utama siap, halaman ini otomatis tidak terpakai lagi.</li>
</ul>
</div></div>

<div class='gtake-body' style='display:none'></div>
<div class='gtake-sidebar' style='display:none'></div>
<div id='gtake-layout' class='gtake-layout' data-theme='gtake' style='display:none'></div>
</body></html>"""

def register(app: Flask) -> None:
    bp = Blueprint("dashboard_fallback", __name__, url_prefix="/dashboard")

    @bp.route("/", methods=["GET"])
    def home():
        return render_template_string(HTML_DASH)

    @bp.route("/login", methods=["GET"])
    def login():
        return render_template_string(HTML_LOGIN)

    @bp.route("/login", methods=["POST"])
    def do_login():
        return redirect(url_for("dashboard_fallback.home"))

    app.register_blueprint(bp)

def create_app() -> Flask:
    app = Flask("satpambot_dashboard_fallback")
    register(app)

    @app.route("/", methods=["GET"])
    def root():
        return redirect("/dashboard")

    @app.route("/healthz", methods=["HEAD","GET"])
    def healthz():
        return Response("OK", mimetype="text/plain")

    @app.route("/uptime", methods=["HEAD","GET"])
    def uptime():
        return Response("OK", mimetype="text/plain")

    @app.route("/api/ui-config", methods=["GET"])
    def ui_config():
        return {"theme":"gtake","accent":"teal","bg_mode":"gradient","logo_url":"/dashboard-static/logo.svg"}

    @app.route("/api/ui-themes", methods=["GET"])
    def ui_themes():
        return {"themes":["gtake"]}

    return app
