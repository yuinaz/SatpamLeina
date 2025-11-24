from __future__ import annotations

import os, time, socket, errno
from typing import Optional

def _port_in_use(host: str, port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.25)
    try:
        return s.connect_ex((host, port)) == 0
    finally:
        s.close()

def run_web_safely(app, host: str = "0.0.0.0", port: Optional[int] = None, max_wait: float = 12.0):
    """
    Start Flask dev server but wait for previous process to release the port.
    - host default 0.0.0.0
    - port default: $PORT or 10000
    - retries for ~max_wait seconds on EADDRINUSE
    - use_reloader=False to avoid double bind
    Usage (in entry/main.py or wherever you run app):
        from satpambot.helpers.web_safe_start import run_web_safely
        run_web_safely(app)
    """
    if port is None:
        try:
            port = int(os.getenv("PORT", "10000"))
        except Exception:
            port = 10000

    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline and _port_in_use("127.0.0.1", port):
        # Previous instance still shutting down; wait a bit
        time.sleep(0.5)

    while True:
        try:
            # Werkzeug/Flask dev server
            app.run(host=host, port=port, use_reloader=False)
            break
        except OSError as e:
            if getattr(e, "errno", None) in (errno.EADDRINUSE, 98, 10048):
                # tiny backoff then retry until deadline; if exceeded, re-raise
                if time.monotonic() < deadline:
                    time.sleep(0.5)
                    continue
            raise
