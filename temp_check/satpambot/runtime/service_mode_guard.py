
import os, logging, importlib
log = logging.getLogger(__name__)

def start():
    mode = os.getenv("SERVICE_MODE", "worker").lower()
    if mode == "worker":
        _start_discord()
    elif mode == "web":
        _start_web()
    elif mode == "both":
        _start_discord(); _start_web()
    else:
        log.warning("Unknown SERVICE_MODE=%s; default worker", mode)
        _start_discord()

def _start_discord():
    try:
        m = importlib.import_module("satpambot.bot.main")
        m.main()
    except Exception as e:
        log.exception("discord worker failed: %r", e)

def _start_web():
    try:
        m = importlib.import_module("satpambot.web.main")
        m.main()
    except Exception as e:
        log.exception("web app failed: %r", e)
