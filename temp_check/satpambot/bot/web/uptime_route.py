from __future__ import annotations

# satpambot/bot/web/uptime_route.py
# ALWAYS-200 uptime endpoint with bot-online status.
import time
try:
    import app as _app_module
    app = getattr(_app_module, "app", None)
except Exception:
    app = None

def _payload():
    # Lazy import to avoid circulars if app imports routes early.
    try:
        from satpambot.bot.helpers import uptime_state
        st = uptime_state.get_state()
    except Exception:
        st = {"online": False, "last_change": int(time.time())}
    return {
        "ok": True,
        "bot_online": bool(st.get("online", False)),
        "since": int(st.get("last_change", int(time.time()))),
        "ts": int(time.time()),
    }

if app is not None:
    @app.get("/uptime")
    def uptime():
        # Always 200 to keep external monitor green.
        return _payload(), 200

    @app.get("/healthz")
    def healthz():
        # Plain health for process liveness (also 200).
        return {"ok": True, "ts": int(time.time())}, 200
