# SatpamBot — Render.com multi-service setup

Patch ini memisahkan **dashboard (web)** dan **bot (worker)** agar stabil dan lulus health check.

## Service
1. **satpambot-dashboard (web)** → `python run_dashboard.py`, health check `GET /healthz`.
2. **satpambot-bot (worker)** → `python run_bot.py`, tidak membuka port.

## Deploy via Blueprint
- Hubungkan repo ke Render → **New → Blueprint** → pilih repo yang berisi `render.yaml` ini.
- Set env var di worker: `DISCORD_TOKEN` (atau `BOT_TOKEN`).
- Set env var di web: kredensial dashboard (mis. `ADMIN_USERNAME`, `ADMIN_PASSWORD`).

Dibuat: 2025-08-19T11:52:52.286421
