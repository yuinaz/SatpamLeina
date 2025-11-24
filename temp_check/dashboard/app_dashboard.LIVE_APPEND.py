
# >>> PATCH: LIVE API (append to your existing app_dashboard.py) <<<
# Tambahan endpoint ringan untuk mendeteksi live server & menarik metrik dari bot.
from flask import jsonify
import time

try:
    from satpambot.dashboard.discord_bridge import get_metrics as _get_metrics, get_bot as _get_bot
except Exception:
    _get_metrics = None
    _get_bot = lambda: None

START_TS = int(time.time())

def register_live_routes(app):
    @app.get("/api/ping")
    def api_ping():
        # sederhana untuk deteksi "Live" (health + epoch)
        return jsonify({"ok": True, "ts": int(time.time()), "uptime_sec": int(time.time() - START_TS)})

    @app.get("/api/metrics")
    def api_metrics():
        if not _get_metrics:
            return jsonify({"ok": False, "reason": "bridge_missing"}), 503
        data = _get_metrics()
        return jsonify(data), (200 if data.get("ok") else 503)
# >>> END PATCH <<<
