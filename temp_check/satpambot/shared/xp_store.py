
"""
xp_store helpers unified to xp:bot:senior_total
"""
import os, json, urllib.request

BASE = (os.getenv("UPSTASH_REDIS_REST_URL") or "").rstrip("/")
TOK  = os.getenv("UPSTASH_REDIS_REST_TOKEN") or ""

def _req(path):
    if not BASE or not TOK: return None
    req = urllib.request.Request(BASE + "/" + path.lstrip("/"), headers={"Authorization": f"Bearer {TOK}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())

def get_senior_total():
    r = _req("get/xp:bot:senior_total")
    return None if r is None else r.get("result")
