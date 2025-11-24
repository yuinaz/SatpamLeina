Patch theme gtake:
- Mengganti hero 'Make Things Simple!' dengan panel 'Live Banned Users' (ol#ban-feed).
- JS: tambahkan isi file `neo_dashboard_live.js.append` ke akhir file `satpambot/dashboard/static/js/neo_dashboard_live.js` milikmu.
- Server: tambahkan blok di `APPEND_TO_app_dashboard.py.txt` ke dalam `satpambot/dashboard/app_dashboard.py` (di bawah import dan sebelum return app). 
  Ini membuat endpoint GET /dashboard/api/bans (membaca data dari data/mod/ban_log.json, data/ban_log.json, dll).
