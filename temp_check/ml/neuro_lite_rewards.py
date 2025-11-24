
import json
from pathlib import Path
from typing import Dict, Any

def _load_json(p: Path) -> Dict[str, Any]:
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_json(p: Path, data: Dict[str, Any]):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    tmp.replace(p)

def _bump_all(d: Dict[str, Any], amount: int):
    d["overall"] = int(d.get("overall", 0)) + amount
    for k in ("TK","SD","CURRICULUM","TRACKS"):
        if isinstance(d.get(k), dict):
            for sub in list(d[k].keys()):
                try:
                    d[k][sub] = int(d[k].get(sub, 0)) + amount
                except Exception:
                    pass

def award_points_all(neuro_dir: str, amount: int = 1, reason: str = "phish_ban"):
    base = Path(neuro_dir)
    juniors = base / "learn_progress_junior.json"
    seniors = base / "learn_progress_senior.json"
    for p in (juniors, seniors):
        data = _load_json(p)
        if not data:
            data = {"overall": 0, "TK": {"L1":0, "L2":0}, "SD": {"L1":0,"L2":0,"L3":0,"L4":0,"L5":0,"L6":0}}
        _bump_all(data, int(amount))
        _save_json(p, data)
