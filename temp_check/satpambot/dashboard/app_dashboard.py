
import os, time, json
from pathlib import Path
from flask import jsonify, redirect, send_from_directory, request

# ---- healthz/ping log silencer ----
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
        pass

# ---- Dashboard extras: aliases, uploads, bans, static ----
def _register_dashboard_extras(app):
    UPLOAD_DIR = Path(__file__).with_name("static") / "uploads"
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    ALLOWED = {".png",".jpg",".jpeg",".gif",".svg",".webp"}

    def _cfg_read():
        ui = Path(__file__).with_name("ui_local.json")
        try:
            if ui.exists():
                return json.loads(ui.read_text("utf-8"))
        except Exception:
            pass
        return {}

    def _cfg_write(d):
        ui = Path(__file__).with_name("ui_local.json")
        try:
            ui.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    @app.post("/dashboard/settings/upload")
    def _settings_upload():
        f = request.files.get("file")
        kind = (request.form.get("type") or "").strip().lower()
        if not f or not kind:
            return jsonify({"ok": False, "error": "file/type required"}), 400
        ext = os.path.splitext(f.filename or "")[1].lower()
        if ext not in ALLOWED:
            return jsonify({"ok": False, "error":"bad file type"}), 400
        name = f"{int(time.time())}_{(f.filename or 'file').replace(' ','_')}"
        path = UPLOAD_DIR / name
        try:
            f.save(path)
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
        url = f"/dashboard-static/uploads/{name}"
        cfg = _cfg_read()
        if kind == "logo": cfg["logo"] = url
        if kind == "background": cfg["bg_url"] = url
        _cfg_write(cfg)
        return jsonify({"ok": True, "url": url})

    @app.get("/dashboard-static/uploads/<path:fname>")
    def _static_uploads(fname):
        return send_from_directory(str(UPLOAD_DIR), fname)

    @app.get("/dashboard/api/metrics")
    def _api_metrics():
        # Try call handler /api/live/stats jika ada
        vf = app.view_functions.get("api_live_stats")
        if vf:
            try:
                return vf()
            except Exception:
                pass
        return jsonify({
            "guilds": 0, "members": 0, "channels": 0, "threads": 0,
            "online": 0, "latency_ms": 0, "updated": int(time.time())
        })

    @app.get("/dashboard/tasks")
    def _alias_tasks():
        return redirect("/dashboard", code=302)

    @app.get("/dashboard/options")
    def _alias_options():
        return redirect("/dashboard/settings", code=302)

    @app.get("/dashboard/api/bans")
    def _api_bans():
        limit = int((request.args.get("limit") or 10))
        cands = [
            Path("data/mod/ban_log.json"),
            Path("data/ban_log.json"),
            Path("data/mod/bans.json"),
        ]
        recs = []
        for p in cands:
            try:
                if p.exists():
                    data = json.loads(p.read_text("utf-8"))
                    if isinstance(data, dict) and "items" in data: data = data["items"]
                    if isinstance(data, list): recs.extend(data)
            except Exception:
                pass
        def norm(x):
            user = x.get("user") or x.get("username") or x.get("tag") or ""
            uid  = x.get("user_id") or x.get("id")
            when = x.get("when") or ""
            if not when:
                ts = x.get("ts") or x.get("timestamp") or x.get("time")
                try:
                    from datetime import datetime, timezone, timedelta
                    if isinstance(ts, (int,float)):
                        wib = datetime.fromtimestamp(int(ts), tz=timezone.utc) + timedelta(hours=7)
                    else:
                        wib = datetime.fromisoformat(str(ts).replace("Z","+00:00")) + timedelta(hours=7)
                    when = wib.strftime("%A, %d/%m/%y")
                except Exception:
                    when = ""
            return {"user": user, "user_id": uid, "when_str": when}
        recs = [norm(r) for r in recs][-limit:]
        return jsonify(recs)

# === SATPAM PATCH (APPEND-ONLY) — jangan hapus kode di atas ===
import os as _satp_os
from flask import Response as _satp_Response

def _satp_route_exists(_app, _path: str) -> bool:
    try:
        for r in _app.url_map.iter_rules():
            if r.rule == _path:
                return True
    except Exception:
        pass
    return False

def _satp_bind_health(_app):
    # /healthz
    if not _satp_route_exists(_app, "/healthz"):
        @_app.route("/healthz", methods=["GET","HEAD"])
        def __satp_healthz_ok():
            return _satp_Response(status=200)
    # /uptime
    if not _satp_route_exists(_app, "/uptime"):
        @_app.route("/uptime", methods=["GET","HEAD"])
        def __satp_uptime_ok():
            return _satp_Response(status=200)
    # alias /login -> /dashboard/login (biar gak 404)
    if not _satp_route_exists(_app, "/login"):
        @_app.get("/login")
        def __satp_login_alias():
            from flask import redirect, url_for
            return redirect(url_for("dashboard.login"))

# panggil ke instance app yang sudah ada di file kamu
try:
    _satp_bind_health(app)
except NameError:
    pass

# kalau file ini dijalankan langsung, tetap hormati PORT
if __name__ == "__main__":
    try:
        _satp_port = int(_satp_os.getenv("PORT", "10000"))
        app.run(host="0.0.0.0", port=_satp_port, debug=False)
    except Exception:
        pass
# === END PATCH ===
