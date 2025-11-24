#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import logging
from logging import handlers as logging_handlers
import threading
import asyncio
from pathlib import Path

# Load local .env file if present
try:
    from dotenv import load_dotenv  # type: ignore
    dotenv_path = Path(".env")
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
except Exception:
    dotenv_path = Path(".env")
    if dotenv_path.exists():
        try:
            for raw in dotenv_path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                if os.getenv(k) is None:
                    os.environ[k] = v
        except Exception:
            pass

# Logging config — keep the format the user expects:
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(levelname)s:%(name)s:%(message)s",
)
log = logging.getLogger("entry.main")

# Import Flask app
from app import app  # noqa: E402

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", os.getenv("WEB_PORT", "10000")))
WEB_THREADS = int(os.getenv("WEB_THREADS", "8"))
WEB_LOG_LEVEL = os.getenv("WEB_LOG_LEVEL", "WARNING").upper()

def _serve_web():
    """Serve the Flask app quietly (waitress -> wsgiref fallback)."""
    try:
        from waitress import serve as waitress_serve  # type: ignore
        logging.getLogger("waitress").setLevel(getattr(logging, WEB_LOG_LEVEL, logging.WARNING))
        waitress_serve(app, host=HOST, port=PORT, threads=WEB_THREADS)
        return
    except Exception:
        from wsgiref.simple_server import make_server, WSGIRequestHandler
        class QuietHandler(WSGIRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                if self.path == "/healthz":
                    pass
                else:
                    super().log_message(format, *args)
        httpd = make_server(HOST, PORT, app, handler_class=QuietHandler)
        httpd.serve_forever()

def _import_shim_runner():
    """Import shim_runner with multiple fallbacks."""
    try:
        from satpambot.bot.modules.discord_bot import shim_runner  # type: ignore
        return shim_runner
    except Exception:
        try:
            import satpambot.bot.shim_runner as shim_runner  # type: ignore
            return shim_runner
        except Exception:
            import satpambot.shim_runner as shim_runner  # type: ignore
            return shim_runner

def main():
    # Optional preflight (non-fatal if missing)
    try:
        import importlib
        _pre = importlib.import_module("scripts.preflight_render_free")
        if hasattr(_pre, "main"):
            _pre.main()
    except Exception as _e:
        logging.getLogger("entry.main").warning("[preflight] WARN: %r", _e)

    # Start web (unless disabled)
    if os.getenv("RUN_WEB", "1") != "0":
        log.info(f"🌐 Serving web on {HOST}:{PORT}")
        t = threading.Thread(target=_serve_web, name="web", daemon=True)
        t.start()
        log.info(f"Web is ready on port {PORT}")
    else:
        log.info("🌐 Web disabled by RUN_WEB=0")

    # File logging to run_YYYYmmdd_HHMMSS.log
    import time, os as _os
    _ts = time.strftime("%Y%m%d_%H%M%S")
    _log_name = f"run_{_ts}.log"
    _root = logging.getLogger()
    if not any(isinstance(h, logging_handlers.RotatingFileHandler) for h in _root.handlers):
        _fh = logging_handlers.RotatingFileHandler(
            _log_name, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        )
        _fh.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
        _root.addHandler(_fh)
        if _root.level > logging.INFO:
            _root.setLevel(logging.INFO)
        logging.getLogger("entry.main").info("📄 file log => %s", _os.path.abspath(_log_name))

    # Start Discord bot
    log.info("🤖 Starting Discord bot (shim_runner.start_bot)...")
    shim_runner = _import_shim_runner()
    asyncio.run(shim_runner.start_bot())

if __name__ == "__main__":
    main()
