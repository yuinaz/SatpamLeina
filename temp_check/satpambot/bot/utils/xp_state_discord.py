import json, logging
log = logging.getLogger(__name__)

DEFAULT_STATE = {"total": 0, "label": None, "percent": 0.0, "remaining": None}

def _coerce_dict(obj):
    if not isinstance(obj, dict):
        return dict(DEFAULT_STATE)
    total = obj.get("total", obj.get("senior_total", obj.get("overall", 0)))
    label = obj.get("label")
    percent = obj.get("percent", 0.0)
    remaining = obj.get("remaining")
    try: total = int(total or 0)
    except Exception: total = 0
    try: percent = float(percent or 0.0)
    except Exception: percent = 0.0
    return {"total": total, "label": label, "percent": percent, "remaining": remaining}

def load(text):
    if text is None:
        return dict(DEFAULT_STATE)
    try:
        if isinstance(text, dict):
            return _coerce_dict(text)
        s = str(text).strip()
        if not s:
            return dict(DEFAULT_STATE)
        data = json.loads(s)
        return _coerce_dict(data)
    except Exception as e:
        log.error("[xp/discord] parse JSON failed: %s", e)
        return dict(DEFAULT_STATE)
