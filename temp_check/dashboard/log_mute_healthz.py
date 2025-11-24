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
