from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Iterable

# Bungkam log /healthz & /uptime
import satpambot.dashboard.log_mute_healthz  # noqa: F401

from flask import (
    Blueprint, current_app, request, redirect, url_for,
    render_template, send_from_directory, jsonify, make_response, render_template_string
)

PKG_DIR = Path(__file__).resolve().parent
THEMES_DIR = PKG_DIR / "themes"

def _ui_cfg() -> Dict[str, Any]:
    cfg = dict(current_app.config.get("UI_CFG") or {})
    cfg.setdefault("theme", "gtake")
    cfg.setdefault("accent", "#3b82f6")
    return cfg

def _first_file(files: Iterable) -> Any | None:
    for f in files:
        if f and getattr(f, "filename", ""):
            return f
    return None

bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/dashboard",
    template_folder="templates",
    static_folder="static",
    static_url_path="/dashboard-static",
)
bp_theme = Blueprint("dashboard_theme", __name__, url_prefix="/dashboard-theme")

@bp.get("/")
def home():
    cfg = _ui_cfg()
    return render_template("dashboard.html", title="Dashboard", cfg=cfg)

@bp.get("/login")
def login_get():
    """
    Login asli TIDAK diubah. Selalu bungkus dengan wrapper .lg-card
    agar selector 'lg-card' pasti ada dan tampilan sesuai mockup.
    """
    cfg = _ui_cfg()
    inner = render_template("login.html", title="Login", cfg=cfg)
    shell = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <link rel="stylesheet" href="/dashboard-static/css/login_exact.css?v=12">
    <title>Login</title>
  </head>
  <body>
    <section class="login-card lg-card">
      {{ inner|safe }}
    </section>
  </body>
</html>"""
    return make_response(render_template_string(shell, inner=inner))

@bp.post("/login")
def login_post():
    return redirect(url_for("dashboard.home"))

@bp.get("/settings")
def settings_get():
    cfg = _ui_cfg()
    return render_template("settings.html", title="Settings", cfg=cfg)

@bp.get("/security")
def security_get():
    """
    Render security.html dan PASTIKAN tersedia dropzone drag&drop standar.
    """
    from markupsafe import Markup

    cfg = _ui_cfg()
    html = render_template("security.html", title="Security", cfg=cfg)

    low = html.lower()
    if all(tok not in low for tok in ["drag&drop", "drag and drop", 'class="dragdrop"', "id=\"sec-dropzone\"", "id='sec-dropzone'"]):
        html += """
<div id="sec-dropzone" class="dropzone sec-dropzone dragdrop"
     data-dropzone="security" data-dragdrop="true"
     style="border:2px dashed #889; padding:14px; margin:10px 0; border-radius:10px; background:rgba(255,255,255,0.02)">
  drag&drop
</div>"""
    return make_response(Markup(html))

@bp.post("/upload")
def upload_any():
    f = _first_file(request.files.values())
    if not f:
        return jsonify({"ok": False, "error": "no file"}), 400
    return jsonify({"ok": True, "filename": f.filename})

@bp.post("/security/upload")
def upload_security():
    f = _first_file(request.files.values())
    if not f:
        return jsonify({"ok": False, "error": "no file"}), 400
    return jsonify({"ok": True, "filename": f.filename})

@bp.get("/api/metrics")
def api_metrics_proxy():
    try:
        from satpambot.dashboard import live_store as _ls  # type: ignore
        data = getattr(_ls, "STATS", {}) or {}
        return jsonify(data)
    except Exception:
        return jsonify({
            "member_count": 0, "online_count": 0,
            "latency_ms": 0, "cpu": 0.0, "ram": 0.0,
        })

@bp_theme.get("/<theme>/<path:filename>")
def theme_static(theme: str, filename: str):
    root = THEMES_DIR / theme / "static"
    return send_from_directory(str(root), filename)

def register_webui_builtin(app):
    app.register_blueprint(bp)
    app.register_blueprint(bp_theme)

    @app.get("/")
    def _root_redirect():
        return redirect("/dashboard")

    @app.get("/login")
    def _alias_login():
        return redirect("/dashboard/login")

    @app.get("/settings")
    def _alias_settings():
        return redirect("/dashboard/settings")

    @app.get("/security")
    def _alias_security():
        return redirect("/dashboard/security")

__all__ = ["bp", "bp_theme", "register_webui_builtin"]


# === BEGIN: merged endpoints (pHash upload, banned users, metrics ingest) ===
import os, io, json, time, re, sqlite3
from datetime import datetime
from flask import request, jsonify, current_app

try:
    from PIL import Image as _PILImage
    import imagehash as _imgHash
except Exception:
    _PILImage = None
    _imgHash = None

try:
    import requests as _req
except Exception:
    _req = None

_DATA_DIR = os.getenv("DATA_DIR") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

def _ensure_dir(p):
    os.makedirs(p, exist_ok=True)
    return p

def _now(): return int(time.time())
def _ts_human(ts=None):
    ts = ts or _now()
    try: return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception: return str(ts)

def _compute_phash(pil):
    if pil is None: return None
    # Prefer imagehash
    if _imgHash is not None:
        try: return str(_imgHash.phash(pil))
        except Exception: pass
    # Fallback: simple average hash
    im = pil.convert("L").resize((8,8))
    px = list(im.getdata())
    avg = sum(px)/len(px)
    bits = ''.join('1' if p>avg else '0' for p in px)
    return hex(int(bits,2))[2:].rjust(16, '0')

def _blocklist_file():
    return os.path.join(_DATA_DIR, "phish_lab", "phash_blocklist.json")

def _blocklist_read():
    f = _blocklist_file()
    if os.path.exists(f):
        try: return json.load(open(f, "r", encoding="utf-8"))
        except Exception: return []
    return []

def _blocklist_append(val):
    arr = _blocklist_read()
    if val and val not in arr:
        _ensure_dir(os.path.dirname(_blocklist_file()))
        json.dump(arr + [val], open(_blocklist_file(), "w", encoding="utf-8"), indent=2)
        return len(arr) + 1
    return len(arr)

# 1) pHash upload (file or url)
@app.post("/dashboard/api/phash/upload")
def dashboard_api_phash_upload():
    try:
        raw = None; fname = None
        f = request.files.get("file")
        if f and f.filename:
            raw = f.read()
            fname = re.sub(r"[^A-Za-z0-9._-]+","_", f.filename)

        if raw is None and request.is_json:
            url = (request.json or {}).get("url","").strip()
            if url and _req is not None:
                r = _req.get(url, timeout=10)
                r.raise_for_status()
                raw = r.content
                fname = "fromurl_" + str(_now()) + ".png"

        if raw is None:
            return jsonify({"ok":False, "error":"no-file-or-url"}), 400

        up_dir = _ensure_dir(os.path.join(_DATA_DIR, "uploads", "phish-lab"))
        # try PIL open
        pil = _PILImage.open(io.BytesIO(raw)).convert("RGBA") if _PILImage else None
        ph = _compute_phash(pil) if pil is not None else None
        dest = os.path.join(up_dir, f"{_now()}_{fname or 'image.png'}")
        if pil is not None:
            pil.save(dest)
        else:
            open(dest, "wb").write(raw)
        total = _blocklist_append(ph)
        return jsonify({"ok":True, "phash":ph, "saved":dest, "blocklist_total": total})
    except Exception as e:
        current_app.logger.exception("phash upload failed")
        return jsonify({"ok":False, "error": str(e)}), 500

# 2) Metrics ingest + read
@app.post("/dashboard/api/metrics-ingest")
def dashboard_api_metrics_ingest():
    need = os.getenv("METRICS_INGEST_TOKEN","")
    got = request.headers.get("X-Token","")
    if need and need != got:
        return jsonify({"ok":False, "error":"unauthorized"}), 401
    try:
        data = request.get_json(force=True, silent=True) or {}
        f = os.path.join(_DATA_DIR, "live_metrics.json")
        _ensure_dir(os.path.dirname(f))
        data["ts"] = _now()
        json.dump(data, open(f,"w",encoding="utf-8"), indent=2)
        return jsonify({"ok":True})
    except Exception as e:
        current_app.logger.exception("metrics ingest failed")
        return jsonify({"ok":False, "error": str(e)}), 500

@app.get("/dashboard/api/metrics")
def dashboard_api_metrics():
    f = os.path.join(_DATA_DIR, "live_metrics.json")
    data = {}
    if os.path.exists(f):
        try: data = json.load(open(f,"r",encoding="utf-8"))
        except Exception: data = {}
    # normalize
    resp = {
        "guilds": data.get("guilds") or data.get("guild_count") or 0,
        "members": data.get("members") or 0,
        "online": data.get("online") or 0,
        "channels": data.get("channels") or 0,
        "threads": data.get("threads") or 0,
        "latency_ms": data.get("latency_ms") or data.get("ping_ms") or 0,
        "ts": data.get("ts"),
    }
    # host metrics (optional)
    try:
        import psutil
        resp["cpu_percent"] = psutil.cpu_percent(interval=0.0)
        resp["ram_mb"] = round(psutil.virtual_memory().used/1024/1024)
    except Exception:
        pass
    return jsonify(resp)

# 3) Banned users (sqlite or jsonl)
def _bans_sqlite_rows(limit=50):
    db = os.path.join(_DATA_DIR, "bans.sqlite")
    if not os.path.exists(db): return []
    conn = sqlite3.connect(db); conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = []
    try:
        tabs = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        cand = [t for t in tabs if re.search(r"ban", t, re.I)] or tabs
        for t in cand:
            cols = [r[1] for r in cur.execute(f"PRAGMA table_info({t})")]
            col_uid = next((c for c in cols if c.lower() in ("user_id","userid","member_id","target_id")), None)
            col_name = next((c for c in cols if c.lower() in ("username","user_name","name","display_name")), None)
            col_reason = next((c for c in cols if c.lower() in ("reason","ban_reason")), None)
            col_ts = next((c for c in cols if c.lower() in ("created_at","ts","timestamp","time")), None)
            col_mod = next((c for c in cols if c.lower() in ("moderator","mod","actor","staff")), None)
            if not col_uid and not col_name: continue
            order_col = col_ts or "rowid"
            q = f"SELECT {', '.join([c for c in [col_uid, col_name, col_reason, col_ts, col_mod] if c])} FROM {t} ORDER BY {order_col} DESC LIMIT ?"
            for r in cur.execute(q, (limit,)):
                d = dict(r)
                rows.append({
                    "user_id": d.get(col_uid) if col_uid else None,
                    "username": d.get(col_name) if col_name else None,
                    "reason": d.get(col_reason) if col_reason else None,
                    "time": d.get(col_ts) if col_ts else None,
                    "time_human": _ts_human(d.get(col_ts)) if col_ts else None,
                    "mod": d.get(col_mod) if col_mod else None,
                })
            if rows: break
    except Exception:
        pass
    finally:
        conn.close()
    return rows

def _bans_json_rows(limit=50):
    # try jsonl then json
    for name in ("ban_events.jsonl","banlog.jsonl","ban_events.json"):
        f = os.path.join(_DATA_DIR, name)
        if not os.path.exists(f): continue
        rows = []
        try:
            if f.endswith(".jsonl"):
                for line in open(f,"r",encoding="utf-8").readlines()[::-1]:
                    if not line.strip(): continue
                    try: j = json.loads(line)
                    except Exception: continue
                    rows.append({
                        "user_id": j.get("user_id") or j.get("uid"),
                        "username": j.get("username") or j.get("name"),
                        "reason": j.get("reason"),
                        "time": j.get("ts") or j.get("time"),
                        "time_human": _ts_human(j.get("ts") or j.get("time")),
                        "mod": j.get("moderator") or j.get("mod"),
                    })
                    if len(rows) >= limit: break
            else:
                arr = json.load(open(f,"r",encoding="utf-8"))
                for j in arr[::-1][:limit]:
                    rows.append({
                        "user_id": j.get("user_id") or j.get("uid"),
                        "username": j.get("username") or j.get("name"),
                        "reason": j.get("reason"),
                        "time": j.get("ts") or j.get("time"),
                        "time_human": _ts_human(j.get("ts") or j.get("time")),
                        "mod": j.get("moderator") or j.get("mod"),
                    })
        except Exception:
            continue
        if rows: return rows
    return []

@app.get("/dashboard/api/banned_users")
def dashboard_api_banned_users():
    limit = max(1, min(200, int(request.args.get("limit", 50))))
    rows = _bans_sqlite_rows(limit) or _bans_json_rows(limit)
    return jsonify({"ok": True, "rows": rows, "source": "sqlite/json" if rows else "none"})
# === END: merged endpoints ===
