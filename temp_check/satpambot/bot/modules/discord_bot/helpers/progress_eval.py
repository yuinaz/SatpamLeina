from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

def _flatten_numbers(d: Any):
    if isinstance(d, dict):
        for v in d.values():
            yield from _flatten_numbers(v)
    elif isinstance(d, list):
        for v in d:
            yield from _flatten_numbers(v)
    else:
        if isinstance(d, (int, float)):
            yield float(d)

def _try_keys(d: dict, keys):
    for k in keys:
        if isinstance(d, dict) and k in d:
            v = d[k]
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, dict):
                for kk in ("percent","percentage","completion","overall"):
                    if kk in v and isinstance(v[kk], (int,float)):
                        return float(v[kk])
    return None

def compute_percent(d: dict) -> float:
    v = _try_keys(d, ("percent","percentage","completion","overall"))
    if v is not None:
        return max(0.0, min(100.0, v))
    nums = [x for x in _flatten_numbers(d) if 0.0 <= x <= 100.0]
    if nums:
        return max(0.0, min(100.0, sum(nums)/len(nums)))
    return 0.0

def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_error": str(e)}

def evaluate_progress(junior_path: Path, senior_path: Path) -> Dict[str, float]:
    j = load_json(junior_path)
    s = load_json(senior_path)
    jp = compute_percent(j)
    sp = compute_percent(s)
    return {"junior_percent": jp, "senior_percent": sp}
