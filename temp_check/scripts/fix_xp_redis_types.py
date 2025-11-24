
#!/usr/bin/env python3
"""
Upstash XP key type fixer (REST-style, no /pipeline JSON).
This avoids HTTP 400 by using endpoints like:
  GET   {BASE}/get/{key}
  GET   {BASE}/incrby/{key}/{n}
  GET   {BASE}/set/{key}/{value}
Env:
  UPSTASH_REDIS_REST_URL
  UPSTASH_REDIS_REST_TOKEN
Usage:
  python scripts/fix_xp_redis_types.py --dry
  python scripts/fix_xp_redis_types.py
"""
import os, sys, json, re, urllib.request, urllib.parse

BASE = os.getenv("UPSTASH_REDIS_REST_URL")
TOK  = os.getenv("UPSTASH_REDIS_REST_TOKEN")
DRY  = ("--dry" in sys.argv) or ("--dry-run" in sys.argv)

if not BASE or not TOK:
    print("ERROR: Set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN", file=sys.stderr)
    sys.exit(2)

def rest(cmd, *parts):
    url = BASE.rstrip("/") + "/" + "/".join([cmd] + [urllib.parse.quote(str(p), safe='') for p in parts])
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOK}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = r.read().decode()
        try:
            return json.loads(data)
        except Exception:
            return {"result": data}

def get_raw(key):
    try:
        r = rest("get", key)
        return r.get("result")
    except Exception as e:
        print(f"WARN get {key} -> {e}", file=sys.stderr)
        return None

def set_raw(key, val):
    try:
        r = rest("set", key, str(val))
        return r
    except Exception as e:
        print(f"WARN set {key} -> {e}", file=sys.stderr)
        return None

def incrby0_ok(key):
    try:
        _ = rest("incrby", key, "0")
        return True
    except Exception:
        return False

def coerce_int(raw):
    if raw is None:
        return 0, "init"
    s = str(raw)
    if re.fullmatch(r"[-+]?\d+", s): return int(s), "str-int"
    try:
        j = json.loads(s)
        if isinstance(j,(int,float)): return int(j), "json-num"
        if isinstance(j,str) and re.fullmatch(r"[-+]?\d+", j): return int(j), "json-str-int"
        if isinstance(j,dict):
            for k in ("senior_total","total","xp","amount","value"):
                v = j.get(k)
                if isinstance(v,(int,float)): return int(v), f"json[{k}]"
                if isinstance(v,str) and re.fullmatch(r"[-+]?\d+", v): return int(v), f"json[{k}]"
    except Exception:
        pass
    ints = re.findall(r"[-+]?\d+", s)
    if ints:
        ints.sort(key=lambda t: (len(t.lstrip("+-")), int(t)), reverse=True)
        return int(ints[0]), "substr"
    return 0, "fallback"

TARGETS = ["xp:bot:senior_total","xp:bot:senior_total_v2","xp:total"]
changes = []

for key in TARGETS:
    raw = get_raw(key)
    if raw is None:
        if not DRY:
            set_raw(key, "0")
        changes.append((key, None, 0, "init"))
        continue

    if incrby0_ok(key):
        continue

    newv, how = coerce_int(raw)
    if not DRY:
        bak = get_raw(key + ":bak")
        if bak is None:
            set_raw(key + ":bak", str(raw))
        set_raw(key, str(newv))
    changes.append((key, raw, newv, how))

print("== XP Redis Coercion Report ==")
print("Total changes:", len(changes))
for row in changes:
    print(row)
