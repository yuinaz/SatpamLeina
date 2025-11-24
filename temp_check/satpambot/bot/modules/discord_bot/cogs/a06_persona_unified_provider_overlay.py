# noqa: E402
"""
Persona Unified Provider Overlay
- Merges personas from 3 sources with precedence:
    Jaison > Sazen > Base (satpambot/config/personas)
- Non-invasive: patches PersonaStore._load_all at runtime.
- Safe for Render Free Plan (no blocking on import).
Env:
  PERSONA_DIR               (base, default: satpambot/config/personas) [handled by core loader]
  SAZEN_PERSONA_DIR         (default: satpambot/config/personas_sazen)
  JAISON_PERSONA_DIR        (default: satpambot/config/personas_jaison)
  PERSONA_PRIORITY          (csv, default: jaison,sazen,base)
"""
import os, logging, glob, yaml
from pathlib import Path

log = logging.getLogger(__name__)

def _deep_merge(a, b):
    # return new dict = a merged with b (b overrides)
    if not isinstance(a, dict): return b
    out = dict(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out
async def setup(bot):
    # Patch only once
    try:
        from satpambot.bot.persona import loader as _loader
    except Exception as e:
        log.warning("[persona-unified] loader not found: %r", e)
        return

    store = _loader.get_store()
    if getattr(store, "_unified_patched", False):
        log.info("[persona-unified] already patched; skip")
        return

    # capture original
    orig = store._load_all

    # Resolve directories
    base_dir  = Path(os.getenv("PERSONA_DIR", "satpambot/config/personas"))
    sazen_dir = Path(os.getenv("SAZEN_PERSONA_DIR", "satpambot/config/personas_sazen"))
    jaison_dir= Path(os.getenv("JAISON_PERSONA_DIR", "satpambot/config/personas_jaison"))

    # priority
    prio_env = os.getenv("PERSONA_PRIORITY", "jaison,sazen,base").lower().split(",")
    PRIO = [p.strip() for p in prio_env if p.strip() in {"base","sazen","jaison"}]
    if not PRIO:
        PRIO = ["jaison","sazen","base"]

    def _load_dir_into(tmp_data, d: Path):
        if not d.exists():
            return
        for p in glob.glob(str(d / "*.yaml")) + glob.glob(str(d / "*.yml")):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                name = Path(p).stem
                # merge with existing
                prev = tmp_data.get(name, {})
                tmp_data[name] = _deep_merge(prev, data)
            except Exception as e:
                log.warning("[persona-unified] load failed for %s: %r", p, e)

    def _unified_load_all(self, force=False):
        # Let original load base (so mtimes/logging stay intact)
        orig(force=force)
        # Start from what loader produced as 'base' snapshot
        tmp = dict(self._data)
        # Build in precedence order
        for tag in PRIO:
            if tag == "base":
                continue  # already included
            elif tag == "sazen":
                _load_dir_into(tmp, sazen_dir)
            elif tag == "jaison":
                _load_dir_into(tmp, jaison_dir)
        # Overwrite store data atomically
        self._data = tmp
        # Preserve active name if still present; else pick first
        active = self.get_active_name()
        if active not in self._data and self._data:
            first = sorted(self._data.keys())[0]
            self.set_active(first)
        # Log
        try:
            log.info("[persona-unified] applied (sources=%s, total=%d, active=%s)",
                     ",".join(PRIO), len(self._data), self.get_active_name())
        except Exception:
            pass

    # patch
    import types
    store._load_all = types.MethodType(_unified_load_all, store)
    store._unified_patched = True
    # Force a first rebuild
    store._load_all(force=True)
    log.info("[persona-unified] ready (priority=%s)", ",".join(PRIO))

# Legacy sync setup for older loader/smoketest
def setup(bot):
    try:
        import asyncio
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
        if loop and loop.is_running():
            return loop.create_task(setup(bot))  # call async setup
        else:
            return asyncio.run(setup(bot))
    except Exception:
        # best-effort; overlay is optional
        return None
