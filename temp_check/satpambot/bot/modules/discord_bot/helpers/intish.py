from __future__ import annotations
import json
from typing import Optional, Tuple
def parse_intish(raw: Optional[str]) -> Tuple[bool, Optional[int]]:
    if raw is None:
        return False, None
    if isinstance(raw, int):
        return True, int(raw)
    s = str(raw).strip()
    if s == "":
        return False, None
    try:
        return True, int(s)
    except Exception:
        pass
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            for k in ("senior_total_xp","total","value","v","xp","count"):
                if k in obj:
                    try:
                        return True, int(obj[k])
                    except Exception:
                        continue
        if isinstance(obj, int):
            return True, int(obj)
    except Exception:
        pass
    return False, None