# patched utils/json.py
import json

def tolerant_loads(s, *args, **kwargs):
    if s is None:
        return None
    try:
        return json.loads(s, **kwargs)
    except Exception:
        try:
            ss = str(s).strip()
            return json.loads(ss, **kwargs)
        except Exception:
            return None

def tolerant_dumps(obj, *args, **kwargs):
    try:
        return json.dumps(obj, **kwargs)
    except Exception:
        return json.dumps(obj, ensure_ascii=False)
