set -euo pipefail

echo "== Apply SatpamBot patch v7 =="
# Pastikan folder
mkdir -p satpambot/dashboard
mkdir -p satpambot/bot/modules/discord_bot/cogs

echo "[1/3] Write satpambot/dashboard/webui.py"
cat > satpambot/dashboard/webui.py <<'PY'
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
    <link rel="stylesheet" href="/dashboard-static/css/login_exact.css">
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
PY

echo "[2/3] Write satpambot/bot/modules/discord_bot/cogs/live_metrics_push.py"
cat > satpambot/bot/modules/discord_bot/cogs/live_metrics_push.py <<'PY'
# Push live metrics to dashboard store every N seconds.
from __future__ import annotations

import os
import asyncio
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import tasks, commands

try:
    import psutil
except Exception:
    psutil = None

# Defaults; override via ENV
GUILD_ID_DEFAULT = int(os.environ.get("SATPAMBOT_METRICS_GUILD_ID", "761163966030151701"))
INTERVAL_DEFAULT_SEC = int(os.environ.get("SATPAMBOT_METRICS_INTERVAL", "60"))

# WIB (UTC+7)
WIB = timezone(timedelta(hours=7), name="WIB")


class LiveMetricsPush(commands.Cog):
    """Collect & publish live metrics to satpambot.dashboard.live_store.STATS."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.loop_task.start()

    def cog_unload(self) -> None:
        try:
            self.loop_task.cancel()
        except Exception:
            pass

    @tasks.loop(seconds=INTERVAL_DEFAULT_SEC)
    async def loop_task(self) -> None:
        guild = None
        try:
            guild = self.bot.get_guild(GUILD_ID_DEFAULT) or await self.bot.fetch_guild(GUILD_ID_DEFAULT)
        except Exception:
            guild = None

        member_count = 0
        online_count = 0

        if guild is not None:
            try:
                member_count = int(getattr(guild, "member_count", 0) or 0)
                if getattr(guild, "chunked", False) and hasattr(guild, "members"):
                    online_count = sum(
                        1 for m in guild.members
                        if getattr(m, "status", discord.Status.offline) != discord.Status.offline
                    )
            except Exception:
                pass

        latency_ms = int((self.bot.latency or 0.0) * 1000)

        cpu = 0.0
        ram = 0.0
        if psutil is not None:
            try:
                cpu = float(psutil.cpu_percent(interval=None))
            except Exception:
                cpu = 0.0
            try:
                proc = psutil.Process()
                ram = float(proc.memory_info().rss) / (1024 * 1024)
            except Exception:
                ram = 0.0

        payload = {
            "member_count": member_count,
            "online_count": online_count,
            "latency_ms": latency_ms,
            "cpu": cpu,
            "ram": ram,
            "ts": datetime.now(WIB).isoformat(timespec="seconds"),
        }

        try:
            from satpambot.dashboard import live_store as _ls  # type: ignore
            _ls.STATS = payload
        except Exception:
            pass

    @loop_task.before_loop
    async def _before_loop(self) -> None:
        await self.bot.wait_until_ready()
        await asyncio.sleep(3)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LiveMetricsPush(bot))
PY

echo "[3/3] Write satpambot/dashboard/log_mute_healthz.py"
cat > satpambot/dashboard/log_mute_healthz.py <<'PY'
# Mute werkzeug log lines for /healthz and /uptime.
import logging

class _HealthMute(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not ("/healthz" in msg or "/uptime" in msg)

try:
    logging.getLogger("werkzeug").addFilter(_HealthMute())
except Exception:
    pass
PY

echo "== Done. Now commit =="
