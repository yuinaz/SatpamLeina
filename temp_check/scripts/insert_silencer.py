import io, re, sys

path = "main.py"
src = io.open(path, "r", encoding="utf-8", errors="ignore").read()

if "SILENCE /api/live" in src:
    print("Silencer already present.")
    sys.exit(0)

silencer = r"""
# === SILENCE /api/live ===
try:
    import logging
    from werkzeug.serving import WSGIRequestHandler

    class _SilenceLive(logging.Filter):
        def filter(self, record):
            try:
                m = record.getMessage()
            except Exception:
                return True
            # drop only /api/live access lines
            return "/api/live" not in m

    # filter akses log werkzeug
    logging.getLogger("werkzeug").addFilter(_SilenceLive())

    # patch handler HTTP agar tidak log /api/live
    _orig_log_request = WSGIRequestHandler.log_request
    def _log_request_sans_live(self, code='-', size='-'):
        p = getattr(self, 'path', '')
        if p.startswith("/api/live"):
            return
        return _orig_log_request(self, code, size)
    WSGIRequestHandler.log_request = _log_request_sans_live
except Exception:
    pass
# === END ===
""".lstrip("\n")

# cari pemanggilan run() pertama
m = re.search(r'^\s*(?:socketio|app)\.run\(', src, flags=re.M)
if not m:
    # tidak ketemu run(), taruh di akhir file sebagai fallback
    out = src.rstrip() + "\n\n" + silencer
else:
    i = m.start()
    # sisipkan tepat sebelum run()
    out = src[:i] + silencer + src[i:]

io.open(path, "w", encoding="utf-8", newline="\n").write(out)
print("Silencer inserted.")
