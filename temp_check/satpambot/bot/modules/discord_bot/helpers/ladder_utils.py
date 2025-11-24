
import json, os, re
from typing import Dict, Tuple, Optional

DEFAULT_ORDER = {
    "junior": ["TK", "SD"],
    "senior": ["SMP", "SMA", "KULIAH"],
}

def load_ladder(path: str) -> Dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def _ordered_categories(group_dict: Dict, group_name: str) -> Tuple[str, ...]:
    if isinstance(group_dict, dict) and group_dict:
        return tuple(group_dict.keys())
    return tuple(DEFAULT_ORDER.get(group_name.lower(), []))

def _sorted_thresholds(level_dict: Dict) -> Tuple[Tuple[str, int], ...]:
    pairs = []
    if not isinstance(level_dict, dict):
        return tuple()
    for k, v in level_dict.items():
        try:
            s = str(k)
            m = re.fullmatch(r"([A-Za-z]+)(\d+)", s) or re.fullmatch(r"[Ll](\d+)", s)
            if m:
                cutoff = int(v)
                idx = int(m.groups()[-1])
                pairs.append((s.upper(), idx, cutoff))
        except Exception:
            pass
    pairs.sort(key=lambda x: x[1])
    return tuple((p[0], p[2]) for p in pairs)

def compute_label_from_group(total_xp: int, group_name: str, ladder_map: Dict) -> Optional[str]:
    group = ladder_map.get(group_name.lower()) or ladder_map.get(group_name.upper())
    if not isinstance(group, dict):
        return None

    order = _ordered_categories(group, group_name)
    last_label = None

    for cat in order:
        levels = _sorted_thresholds(group.get(cat, {}))
        if not levels:
            continue
        for level_key, cutoff in levels:
            label = f"{cat.upper()}-{level_key}"
            if total_xp < cutoff:
                return label
            last_label = label
    return last_label
