
"""
Persona loader (Render Free-friendly)
- Loads YAML persona files from satpambot/config/personas/*.yaml
- Simple polling hot-reload (POLL_SEC env, default 5s)
- Public API:
    PersonaStore.get_active() -> dict
    PersonaStore.set_active(name) -> bool
    PersonaStore.list_names() -> list[str]
"""
import os, time, logging, threading, glob, yaml
from pathlib import Path

log = logging.getLogger(__name__)
POLL_SEC = int(os.getenv("PERSONA_POLL_SEC", "5"))
DIR = os.getenv("PERSONA_DIR", "satpambot/config/personas")
ACTIVE_NAME = os.getenv("PERSONA_ACTIVE_NAME", "default")

class PersonaStore:
    def __init__(self, directory: str = DIR, active: str = ACTIVE_NAME):
        self.dir = Path(directory)
        self._mtimes = {}
        self._data = {}
        self._active = active
        self._load_all(force=True)
        t = threading.Thread(target=self._watch, daemon=True)
        t.start()

    def _watch(self):
        while True:
            time.sleep(POLL_SEC)
            try: self._load_all()
            except Exception as e: log.debug("[persona] watch err: %r", e)

    def _load_all(self, force=False):
        changed = False
        for p in glob.glob(str(self.dir / "*.yaml")) + glob.glob(str(self.dir / "*.yml")):
            try:
                mt = os.path.getmtime(p)
                if force or self._mtimes.get(p) != mt:
                    with open(p, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                    name = Path(p).stem
                    self._data[name] = data
                    self._mtimes[p] = mt
                    changed = True
            except FileNotFoundError:
                continue
            except Exception as e:
                log.warning("[persona] load failed for %s: %r", p, e)
        if changed:
            log.info("[persona] reloaded (%d personas), active=%s", len(self._data), self._active)

    def list_names(self):
        return sorted(self._data.keys())

    def set_active(self, name: str):
        if name in self._data:
            self._active = name
            log.info("[persona] active -> %s", name)
            return True
        return False

    def get_active_name(self):
        return self._active

    def get_active(self):
        return self._data.get(self._active) or {}

# singleton helper (optional)
_store = None
def get_store():
    global _store
    if _store is None:
        _store = PersonaStore()
    return _store
