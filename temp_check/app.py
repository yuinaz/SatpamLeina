"""
Flask entry for SatpamBot (single process friendly)
- Stable /healthz and /uptime (200)
- Quiet logs for health endpoints
- Registers dashboard web UI (blueprints, static alias, themes)
- /botlive now uses the same live stats source as /api/live/stats (freshness-based)
"""
from __future__ import annotations

import os, time, logging
from typing import Optional, Tuple
from flask import Flask, jsonify, Response, redirect, request

_START_TS = time.time()

class _HealthAccessFilter(logging.Filter):
    SILENT = ("/healthz", "/uptime")
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            msg = str(record.msg)
        return not any(s in msg for s in self.SILENT)

def _probe_bot() -> Tuple[bool, Optional[int], Optional[float]]:
    """
    Determine bot liveness using the same data used by /api/live/stats.
    Rule: consider alive if metrics 'ts' is fresh (<300s) AND (online>0 or guilds>=1).
    Returns (alive, guilds, latency_ms)
    """
    alive = False; guilds = None; latency_ms = None
    now = int(time.time())
    try:
        # Import the live metrics reader used by dashboard API
        from satpambot.dashboard.webui import _read_metrics_payload  # type: ignore
        data = _read_metrics_payload()
        if isinstance(data, dict):
            ts = int(data.get("ts") or 0)
            guilds = data.get("guilds")
            online = data.get("online") or 0
            latency_ms = data.get("latency_ms")
            fresh = (now - ts) < 300 if ts else False
            alive = bool(fresh and ((online and online > 0) or (guilds and guilds >= 1)))
    except Exception:
        # Fallback to optional internal state (if available)
        try:
            from satpambot.bot.modules.discord_bot import live_metrics  # type: ignore
            st = getattr(live_metrics, "STATE", None)
            if st and isinstance(st, dict):
                guilds = st.get("guilds")
                latency_ms = st.get("latency_ms")
                alive = bool(st.get("alive", False))
        except Exception:
            pass
    return alive, guilds, latency_ms

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev")

    # Quiet werkzeug access log for health checks
    try:
        wz = logging.getLogger("werkzeug")
        wz.addFilter(_HealthAccessFilter())
        app.logger.addFilter(_HealthAccessFilter())
    except Exception:
        pass

    # ------------------- Basic routes -------------------
    @app.route("/healthz", methods=["GET", "HEAD"])
    def _healthz() -> Response:
        if request.method == "HEAD":
            return Response(status=200)
        return Response("ok", status=200, mimetype="text/plain")

    @app.route("/uptime", methods=["GET", "HEAD"])
    def _uptime():
        if request.method == "HEAD":
            return Response(status=200)
        now = time.time()
        return jsonify({
            "uptime_s": int(now - _START_TS),
            "pid": os.getpid(),
            "port": int(os.environ.get("PORT", "10000")),
            "ts": int(now)
        })

    # Root -> dashboard
    @app.route("/", methods=["GET"])
    def _root():
        return redirect("/dashboard", code=302)

    # Bot liveness derived from live stats freshness
    @app.get("/botlive")
    def _botlive():
        alive, guilds, latency_ms = _probe_bot()
        return jsonify({"alive": alive, "guilds": guilds, "latency_ms": latency_ms}), (200 if alive else 503)

    # ------------------- Register dashboard web UI -------------------
    try:
        from satpambot.dashboard.webui import register_webui_builtin  # type: ignore
        register_webui_builtin(app)
    except Exception as e:
        app.logger.warning("dashboard webui not registered: %s", e)

    return app

# WSGI entry for gunicorn or direct run
app = create_app()

# --- robots.txt (lightweight; good for Free plan) ---
try:
    from flask import Response
except Exception:
    Response = None

if Response is not None and 'robots_txt' not in globals():
    @app.route("/robots.txt", methods=["GET", "HEAD"])
    def robots_txt():
        # Disallow crawling API/dashboard; allow root. Cache for 1 day.
        body = "User-agent: *\nDisallow: /api/\nDisallow: /dashboard\nAllow: /\n"
        resp = Response(body, mimetype="text/plain; charset=utf-8")
        resp.headers.setdefault("Cache-Control", "public, max-age=86400, immutable")
        return resp
# --- end robots.txt ---
