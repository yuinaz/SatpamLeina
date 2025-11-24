import os, json
from pathlib import Path

_JSON_PATH = os.getenv("XP_JSON_PATH") or "data/xp_state.json"

def _ensure_dir():
    p = Path(_JSON_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

async def save(total: int, level: str, id: str = "global"):
    p = _ensure_dir()
    try:
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
    except Exception:
        data = {}
    data[id] = {"total": int(total), "level": str(level)}
    tmp = p.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(p)

async def load(id: str = "global"):
    p = _ensure_dir()
    if not p.exists():
        return None, None
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None, None
    rec = data.get(id)
    if not rec:
        return None, None
    return int(rec.get("total", 0)), str(rec.get("level", "TK"))
