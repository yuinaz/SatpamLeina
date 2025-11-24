
import json, os
from typing import Dict, Any
from satpambot.config.compat_conf import get as cfg

DEFAULT_DIR = cfg("NEURO_LITE_DIR", "data/neuro-lite", str)
JUNIOR_FILE = os.path.join(DEFAULT_DIR, "learn_progress_junior.json")
SENIOR_FILE = os.path.join(DEFAULT_DIR, "learn_progress_senior.json")

SKELETON_JUNIOR = {
    "overall": 0.0,
    "TK": {"L1": 0, "L2": 0},
    "SD": {"L1": 0, "L2": 0, "L3": 0, "L4": 0, "L5": 0, "L6": 0},
}
SKELETON_SENIOR = {"overall": 0.0}

def _ensure_parent(p):
    os.makedirs(os.path.dirname(p), exist_ok=True)

def _load(path: str, skeleton: Dict[str, Any]) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        _ensure_parent(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(skeleton, f, indent=2, ensure_ascii=False)
        return json.loads(json.dumps(skeleton))
    except Exception:
        return json.loads(json.dumps(skeleton))

def _save(path: str, obj: Dict[str, Any]):
    _ensure_parent(path)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def _overall_from(obj: Dict[str, Any]) -> float:
    leaves = []
    for k, v in obj.items():
        if isinstance(v, dict):
            for lv in v.values():
                if isinstance(lv, (int, float)):
                    leaves.append(float(lv))
    if not leaves:
        return float(obj.get("overall", 0.0))
    return round(sum(leaves) / len(leaves), 2)

def load_junior() -> Dict[str, Any]:
    return _load(JUNIOR_FILE, SKELETON_JUNIOR)

def load_senior() -> Dict[str, Any]:
    return _load(SENIOR_FILE, SKELETON_SENIOR)

def bump_progress(stage: str, level: str, delta: float = 1.0) -> Dict[str, Any]:
    j = load_junior()
    try:
        j[stage][level] = max(0.0, min(100.0, float(j[stage].get(level, 0.0)) + float(delta)))
    except Exception:
        pass
    j['overall'] = _overall_from(j)
    _save(JUNIOR_FILE, j)
    return j

def set_overall(junior: Dict[str, Any] = None):
    if junior is None:
        junior = load_junior()
    junior['overall'] = _overall_from(junior)
    _save(JUNIOR_FILE, junior)

def ensure_files():
    _ = load_junior()
    _ = load_senior()
