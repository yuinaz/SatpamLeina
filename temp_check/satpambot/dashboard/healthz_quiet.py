from __future__ import annotations

import logging
from flask import Response

def ensure_healthz_route(app):
    if any(r.rule == "/healthz" for r in app.url_map.iter_rules()):
        return
    @app.get("/healthz")
    def _healthz():
        return Response("OK", mimetype="text/plain")

class _HealthzFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/healthz" not in str(getattr(record, "msg", ""))

def silence_healthz_logs(app):
    logging.getLogger("werkzeug").addFilter(_HealthzFilter())
