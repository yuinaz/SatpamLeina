
# --- PATCH: add endpoints below into app_dashboard.py ---
# 1) POST /dashboard/settings/upload  (save logo/bg to dashboard-static/uploads and write ui_local.json)
# 2) GET  /dashboard/api/metrics       (fallback to /api/live/stats)
# 3) GET  /dashboard/api/bans          (read from data/mod/ban_log.json)

