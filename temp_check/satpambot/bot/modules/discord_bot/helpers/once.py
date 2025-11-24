import time, threading
from collections import OrderedDict

class _TTLSet:
    def __init__(self, maxlen=4096):
        self._d = OrderedDict()
        self._lock = threading.Lock()
        self._maxlen = maxlen

    def add_if_new(self, key: str, ttl: float = 10.0) -> bool:
        now = time.monotonic()
        with self._lock:
            # purge
            expired = [k for k,(exp,_) in self._d.items() if exp <= now]
            for k in expired: self._d.pop(k, None)
            if key in self._d:  # sudah pernah
                return False
            self._d[key] = (now + ttl, 1)
            if len(self._d) > self._maxlen:
                self._d.popitem(last=False)
            return True

_reg = _TTLSet()

def once_sync(key: str, ttl: float = 10.0) -> bool:
    """Versi sync; True kalau baru, False kalau duplikat."""
    return _reg.add_if_new(key, ttl)

async def once(key: str, ttl: float = 10.0) -> bool:
    """Versi async; True kalau baru, False kalau duplikat."""
    return _reg.add_if_new(key, ttl)
