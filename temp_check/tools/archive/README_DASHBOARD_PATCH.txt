
DashBoard Final Patch (add-only, idempotent)
===========================================
1) Extract into project root:
   unzip -o dashboard_final_patch.zip -d .

2) Apply patch (append fallbacks & create missing assets only):
   python scripts/apply_dashboard_patch.py

3) Smoke test locally (no bot run):
   python scripts/smoketest_dashboard.py
   # Expect 200 for GET /dashboard/login, 303 for POST /dashboard/login,
   # 200 for /dashboard-static assets, /favicon.ico, /uptime, /api/ui-config

4) Commit & push once:
   git add -A
   git commit -m "dashboard: center login + static alias + favicon + safe fallbacks (add-only)"
   git push -u origin main

Notes:
- Script only creates files if missing; existing correct files are left untouched.
- webui.py fallback block is appended once (guarded by marker).
- No env changes; no config rewrites.
