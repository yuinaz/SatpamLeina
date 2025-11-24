# sitecustomize.py — tolerant JSON/YAML; never crash consumer code.
import sys, types, json, re, logging
log = logging.getLogger("sitecustomize:tolerant")

def _sanitize_json(s: str) -> str:
    if s is None: return ""
    if not isinstance(s, str):
        try: s = s.decode("utf-8", "ignore")
        except Exception: s = str(s)
    s = s.replace("\x00", "")
    s = re.sub(r',\s*([}\]])', r'\1', s)  # strip trailing commas
    return s.strip()

def tolerant_loads(s, cls=None, **kwargs):
    try:
        return json.loads(s, cls=cls, **kwargs)
    except Exception:
        try:
            return json.loads(_sanitize_json(s), cls=cls, **kwargs)
        except Exception as e:
            log.debug("tolerant_loads fail: %r", e)
            return {}

def tolerant_dumps(obj, **kwargs):
    try:
        return json.dumps(obj, **kwargs)
    except Exception:
        try:
            return json.dumps(obj, ensure_ascii=False)
        except Exception:
            return "{}"

shim = types.SimpleNamespace(tolerant_loads=tolerant_loads, tolerant_dumps=tolerant_dumps)
sys.modules.setdefault("satpambot.bot.modules.discord_bot.helpers.selfheal_json", shim)
sys.modules.setdefault("satpambot.bot.modules.discord_bot.helpers.json_selfheal", shim)
