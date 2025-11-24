
# smoke_xp_state_fixed.py
# Usage:
#   set env:
#     UPSTASH_REDIS_REST_URL=https://...upstash.io
#     UPSTASH_REDIS_REST_TOKEN=...
#   python smoke_xp_state_fixed.py
#
import os, json, sys, urllib.request

BASE = os.getenv("UPSTASH_REDIS_REST_URL", "").strip()
TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()

def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)

if not BASE or not TOKEN:
    die("Env UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN belum di-set.")

print(f"[xp-smoke] Base URL : {BASE}")
print(f"[xp-smoke] Token    : set({len(TOKEN)} chars)")

def http_get(path):
    req = urllib.request.Request(
        url=f"{BASE}{path}",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def http_post_json(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=f"{BASE}{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw)

# First try pipeline with proper JSON array (per docs)
cmds = [
    ["GET", "xp:store"],
    ["GET", "xp:bot:senior_total"],
    ["GET", "xp:ladder:TK"],
]

try:
    res = http_post_json("/pipeline", cmds)
    print("[pipeline] OK")
    for i, item in enumerate(res):
        print(f"  [{i}] {item}")
    sys.exit(0)
except Exception as e:
    print(f"[pipeline] fallback: {e!r}")

# Fallback to individual GETs
keys = ["xp:store", "xp:bot:senior_total", "xp:ladder:TK"]
for k in keys:
    try:
        r = http_get(f"/get/{k}")
        print(f"[get] {k} -> {r}")
    except Exception as e:
        print(f"[get] {k} -> ERROR: {e!r}")
