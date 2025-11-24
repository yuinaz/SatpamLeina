# === webui LIVE APPEND ===
# Place near the top of webui.py (after imports):
#   import satpambot.dashboard.log_mute_healthz  # noqa: F401
#
# Add/replace route to pass cfg into security.html
# inside blueprint module:
@bp.get("/security")
def security():
    from flask import current_app, render_template
    cfg = current_app.config.get("UI_CFG") or {}
    return render_template("security.html", title="Security", cfg=cfg)

# Optional compatibility alias for theme script
@bp.get("/dashboard/api/metrics")
def dashboard_metrics():
    from flask import jsonify
    # proxy to global live stats (or return zeros)
    try:
        from satpambot.dashboard import live_store as _ls
        data = getattr(_ls, "STATS", {}) or {}
        return jsonify(data)
    except Exception:
        return jsonify({"member_count": 0, "online_count": 0, "latency_ms": 0, "cpu": 0.0, "ram": 0.0})
