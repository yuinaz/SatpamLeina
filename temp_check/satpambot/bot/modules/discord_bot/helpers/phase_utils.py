from __future__ import annotations
import os, json
from pathlib import Path

# Keys for Upstash
PHASE_KEY = os.getenv("LEARNING_PHASE_KEY", "learning:phase")
TK_KEY    = os.getenv("TK_XP_KEY", "xp:bot:tk_total")
SENIOR_KEY= os.getenv("SENIOR_XP_KEY", "xp:bot:senior_total")

def _upstash_enabled():
    return os.getenv("KV_BACKEND") == "upstash_rest" and os.getenv("UPSTASH_REDIS_REST_URL") and os.getenv("UPSTASH_REDIS_REST_TOKEN")

def _http_post(url, token, path, data: bytes):
    try:
        import requests  # type: ignore
        r = requests.post(url.rstrip("/") + path, data=data, headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain"}, timeout=10)
        return r.status_code, r.text
    except Exception:
        import urllib.request
        req = urllib.request.Request(url.rstrip("/") + path, data=data, headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            txt = resp.read().decode("utf-8","ignore")
            return 200, txt

def _http_get(url, token, path):
    try:
        import requests  # type: ignore
        r = requests.get(url.rstrip("/") + path, headers={"Authorization": f"Bearer {token}"}, timeout=10)
        return r.status_code, r.text
    except Exception:
        import urllib.request
        req = urllib.request.Request(url.rstrip("/") + path, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            txt = resp.read().decode("utf-8","ignore")
            return 200, txt

def upstash_get(key: str):
    """Return the Upstash *result* field (already unwrapped).

    Upstash REST `GET /get/<key>` returns JSON like:
      {"result":"<value>"}  or  {"result":null}
    We return (value, None) where value may be str|None.
    """
    if not _upstash_enabled(): return None, "disabled"
    url = os.getenv("UPSTASH_REDIS_REST_URL"); token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    code, txt = _http_get(url, token, "/get/" + key)
    if code != 200:
        return None, f"HTTP {code}"
    try:
        obj = json.loads(txt)
        return obj.get("result", None), None
    except Exception:
        # If server didn't return JSON, pass it through.
        return txt, None

def upstash_set(key: str, value: str):
    if not _upstash_enabled(): return False, "disabled"
    url = os.getenv("UPSTASH_REDIS_REST_URL"); token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    code, txt = _http_post(url, token, "/set/" + key, value.encode("utf-8"))
    ok = (code == 200 and "OK" in txt.upper())
    return ok, txt[:200]

# ---- Local files (fallback) ----
TK_FILE = Path("data/learn/tk_xp.json")
SENIOR_FILE = Path("data/learn/senior_xp.json")
PHASE_FILE = Path("data/learn/phase.json")

def _read_json(path: Path):
    if path.exists():
        try: return json.loads(path.read_text(encoding="utf-8"))
        except Exception: pass
    return {}

def _write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def get_phase() -> str:
    # Upstash first (unwrapped result)
    val, _ = upstash_get(PHASE_KEY)
    if val:
        # val may be JSON string or plain string ("senior")
        try:
            obj = json.loads(val)
            return str(obj.get("phase", "junior"))
        except Exception:
            return str(val)
    # local fallback
    obj = _read_json(PHASE_FILE)
    return str(obj.get("phase", "junior"))

def set_phase(new_phase: str):
    payload = json.dumps({"phase": new_phase}, ensure_ascii=False)
    ok, _ = upstash_set(PHASE_KEY, payload)
    _write_json(PHASE_FILE, {"phase": new_phase})
    return ok

def _parse_numeric_or_json(val, field: str):
    if val is None:
        return None
    # If Upstash result is JSON string, parse and read field
    try:
        obj = json.loads(val)
        if isinstance(obj, dict) and field in obj:
            return int(obj.get(field, 0))
    except Exception:
        # If plain number string
        try:
            return int(str(val).strip())
        except Exception:
            return None
    return None

def get_tk_total() -> int:
    val, _ = upstash_get(TK_KEY)  # val is already the "result" field
    parsed = _parse_numeric_or_json(val, "tk_total_xp")
    if isinstance(parsed, int):
        return parsed
    obj = _read_json(TK_FILE)
    return int(obj.get("tk_total_xp", obj.get("total_xp", 0)))

def add_tk_xp(delta: int):
    cur = max(0, get_tk_total())
    new = cur + int(delta)
    payload = json.dumps({"tk_total_xp": new}, ensure_ascii=False)
    ok, _ = upstash_set(TK_KEY, payload)
    if not ok:
        obj = _read_json(TK_FILE); obj["tk_total_xp"] = new; _write_json(TK_FILE, obj)
    return new

def get_senior_total() -> int:
    val, _ = upstash_get(SENIOR_KEY)
    parsed = _parse_numeric_or_json(val, "senior_total_xp")
    if isinstance(parsed, int):
        return parsed
    obj = _read_json(SENIOR_FILE)
    return int(obj.get("senior_total_xp", obj.get("total_xp", 0)))

def add_senior_xp(delta: int):
    cur = max(0, get_senior_total())
    new = cur + int(delta)
    payload = json.dumps({"senior_total_xp": new}, ensure_ascii=False)
    ok, _ = upstash_set(SENIOR_KEY, payload)
    if not ok:
        obj = _read_json(SENIOR_FILE); obj["senior_total_xp"] = new; _write_json(SENIOR_FILE, obj)
    return new