import time
_PROCESSED = {}
def should_process(msg_id: int, ttl: float = 60.0) -> bool:
    now = time.time()
    for k, v in list(_PROCESSED.items()):
        if now - v > ttl:
            _PROCESSED.pop(k, None)
    if msg_id in _PROCESSED: return False
    _PROCESSED[msg_id] = now
    return True
