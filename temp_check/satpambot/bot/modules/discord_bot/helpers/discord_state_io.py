import logging, json
log = logging.getLogger(__name__)

def import_state(text):
    """Return a dict or {}. Accepts None, JSON string, or dict."""
    if text is None:
        return {}
    if isinstance(text, dict):
        return text
    try:
        return json.loads(str(text))
    except Exception:
        return {}

def export_state(state=None, limit_tokens=800):
    """Return JSON string with safe fields. limit_tokens ignored for simplicity."""
    if state is None:
        state = {}
    try:
        s = json.dumps(state)
    except Exception:
        s = "{}"
    return s

def apply_state(obj):
    """Safely apply state; ignore None or missing fields."""
    if not obj or not isinstance(obj, dict):
        log.info("[state_io] empty/None state, skip apply")
        return
    try:
        for emo, sent, succ in obj.get("sticker_stats", []):
            pass  # placeholder
    except Exception as e:
        log.debug("[state_io] apply sticker_stats skipped: %s", e)
