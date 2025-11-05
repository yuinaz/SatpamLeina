
import os, json
from pathlib import Path
from collections import OrderedDict

def _load_dotenv(path: str = ".env") -> dict:
    out = {}
    p = Path(path)
    if not p.exists(): return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

def _load_overrides(path: str = "data/config/overrides.render-free.json") -> dict:
    p = Path(path)
    if not p.exists(): return {}
    data = json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)
    env = data.get("env") or {}
    # filter to str keys only
    return {str(k): str(v) for k, v in env.items() if isinstance(k, str)}

def export_env():
    over = _load_overrides()
    dot = _load_dotenv()
    merged = {}
    merged.update(over)
    merged.update(dot)  # .env takes precedence
    # export
    for k, v in merged.items():
        if k and v and isinstance(k, str):
            os.environ.setdefault(k, str(v))
    return merged
