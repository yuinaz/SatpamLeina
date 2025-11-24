from collections import defaultdict, deque
from typing import Deque, Dict, Tuple

# Very small in-memory chat history per user (role, content)
class MemoryStore:
    def __init__(self, max_len: int = 20):
        self.max_len = max_len
        self._buf: Dict[int, Deque[Tuple[str,str]]] = defaultdict(lambda: deque(maxlen=self.max_len))

    def add(self, user_id: int, role: str, content: str):
        self._buf[user_id].append(("assistant" if role not in ("user","assistant") else role, content))

    def recent(self, user_id: int, limit: int = 6):
        d = self._buf[user_id]
        return list(enumerate(list(d)[-limit:]))
