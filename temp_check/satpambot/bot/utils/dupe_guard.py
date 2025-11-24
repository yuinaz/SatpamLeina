
import time, hashlib
from typing import Dict, Tuple

class DuplicateSuppressor:
    def __init__(self, ttl_seconds: int = 180):
        self.ttl = ttl_seconds
        self._store: Dict[Tuple[int,str], Tuple[str,float]] = {}

    def _digest(self, payload: str) -> str:
        return hashlib.sha256(payload.encode("utf-8", "ignore")).hexdigest()

    def should_skip(self, channel_id: int, key: str, payload: str) -> bool:
        now = time.time()
        d = self._digest(payload)
        k = (channel_id, key)
        last = self._store.get(k)
        if last and last[0] == d and (now - last[1]) < self.ttl:
            return True
        self._store[k] = (d, now)
        return False
