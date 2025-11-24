LOG_FLAGS = set()

def log_once(key: str, printer):
    if key in LOG_FLAGS:
        return
    LOG_FLAGS.add(key)
    try:
        printer()
    except Exception:
        pass
