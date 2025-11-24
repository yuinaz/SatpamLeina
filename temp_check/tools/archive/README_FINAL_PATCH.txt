
SatpamBot FINAL PATCH (Dashboard + Sticky + Bans + Healthz)

1) Copy & overwrite paths berikut ke repo kamu:
   - satpambot/bot/modules/discord_bot/cogs/sticky_status.py
   - satpambot/bot/modules/discord_bot/cogs/ban_logger.py
   - satpambot/dashboard/app_dashboard.py   # memasang: /dashboard/api/metrics, /dashboard/api/bans, /dashboard/settings/upload, alias tasks/options, & filter log
   - satpambot/dashboard/static/js/neo_dashboard_live.js
   - satpambot/dashboard/templates/security.html
   - satpambot/dashboard/templates/settings.html
   - satpambot/dashboard/themes/gtake/templates/dashboard.html
   - sitecustomize.py  # opsional; set PYTHONPATH=. agar aktif

2) ENV (disarankan, cegah double sticky):
   DISABLED_COGS=sticky_guard,status_sticky_patched

3) Restart web + bot.

Verifikasi:
- Log: tidak ada spam "GET /healthz" / "/api/ping"
- #log-botphising: hanya 1 status + 1 latency (di-edit, bukan post baru)
- Dashboard: DnD jalan, mini-monitor terisi, Settings bisa upload logo/bg, Live Banned Users muncul
