
from __future__ import annotations
import json, os, time
from pathlib import Path
from typing import Any, Dict

class AtomicJsonStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Any] = {}
        self._loaded = False
    def load(self) -> None:
        if self._loaded: return
        if self.path.exists():
            txt = self.path.read_text(encoding='utf-8', errors='ignore')
            if txt.strip(): self._data = json.loads(txt)
        else: self._data = {}
        self._loaded = True
    def get(self) -> Dict[str, Any]:
        self.load(); return self._data
    def write_atomic(self) -> None:
        self.load()
        tmp = self.path.with_suffix('.tmp.%d' % int(time.time()*1000))
        tmp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(tmp, self.path)
    def update(self, fn) -> None:
        self.load(); fn(self._data); self.write_atomic()
