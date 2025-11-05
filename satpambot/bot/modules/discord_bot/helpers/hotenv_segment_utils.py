
import json, hashlib, re
from collections import OrderedDict
from typing import Dict, Tuple

SENTINEL_PREFIX = "---------------- "

def _ordered_env_from_json(j: dict) -> "OrderedDict[str, str]":
    # Keep original order if possible
    if isinstance(j, OrderedDict):
        return j
    if isinstance(j, dict):
        return OrderedDict(j.items())
    raise ValueError("env must be an object")

def split_segments(env_od: "OrderedDict[str, str]") -> "OrderedDict[str, OrderedDict]":
    segs = OrderedDict()
    current = "ROOT"
    segs[current] = OrderedDict()
    for k, v in env_od.items():
        if isinstance(k, str) and k.startswith(SENTINEL_PREFIX):
            current = k.strip()
            if current not in segs:
                segs[current] = OrderedDict()
            continue
        segs[current][k] = v
    return segs

def _stable_dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',',':'))

def sha1_segments(env_od: "OrderedDict[str, str]") -> Dict[str, str]:
    segs = split_segments(env_od)
    out = {}
    for name, items in segs.items():
        out[name] = hashlib.sha1(_stable_dump(items).encode('utf-8')).hexdigest()
    return out

def diff_segments(prev: Dict[str,str], curr: Dict[str,str]) -> Tuple[list, list, list]:
    added = [k for k in curr.keys() if k not in prev]
    removed = [k for k in prev.keys() if k not in curr]
    changed = [k for k in curr.keys() if k in prev and prev[k] != curr[k]]
    return added, removed, changed
