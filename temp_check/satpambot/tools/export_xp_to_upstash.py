
#!/usr/bin/env python3
"""
satpambot/tools/export_xp_to_upstash.py

Gunanya:
- Membaca sumber data XP dan menulis ke Upstash dalam format baru:
  * Hash "xp:bucket:senior:users" (per user)
  * Hash "xp:bucket:reasons" (opsional)
  * String "xp:bot:senior_total" (INT)
  * String "xp:bot:senior_detail" (JSON)
  * String "xp:u:<uid>" (per-user total)

Sumber data yang didukung (prioritas):
1) --from-upstash-store       → GET "xp:store" (JSON {uid:int})
2) --from-json <file.json>    → file JSON {uid:int} atau list event {uid,delta,reason}
3) --from-bridge              → data/neuro-lite/bridge_senior.json (kalau ada)

Contoh:
  python -m satpambot.tools.export_xp_to_upstash --from-upstash-store --reason import --l1 2000

ENV:
  UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN
"""
import os, sys, json, argparse, time
from pathlib import Path

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN","")

def pipeline(cmds):
    import httpx
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        print("[ERR] UPSTASH_REDIS_* env tidak di-set", file=sys.stderr)
        sys.exit(2)
    with httpx.Client(timeout=20.0) as cli:
        r = cli.post(f"{UPSTASH_URL}/pipeline", json=cmds, headers={
            "Authorization": f"Bearer {UPSTASH_TOKEN}"
        })
        r.raise_for_status()
        return r.json()

def get(key):
    import httpx
    with httpx.Client(timeout=10.0) as cli:
        r = cli.get(f"{UPSTASH_URL}/get/{key}")
        if r.status_code != 200:
            return None
        return r.json().get("result")

def load_from_upstash_store():
    raw = get("xp%3Astore")
    try:
        return json.loads(raw) if raw else {}
    except Exception:
        return {}

def load_from_json(path: Path):
    data = json.loads(path.read_text("utf-8"))
    if isinstance(data, dict):
        return data
    # list events
    agg = {}
    for ev in data:
        uid = int(ev.get("uid") or ev.get("user_id") or 0)
        delta = int(ev.get("delta") or ev.get("amount") or 0)
        if uid and delta:
            agg[uid] = agg.get(uid, 0) + delta
    return agg

def load_from_bridge():
    p = Path("data/neuro-lite/bridge_senior.json")
    if not p.exists():
        return {}
    try:
        j = json.loads(p.read_text("utf-8"))
        users = j.get("users") or {}
        # expect {"<uid>": {"xp": int}}
        return {int(k): int(v.get("xp",0)) for k,v in users.items() if str(k).isdigit()}
    except Exception:
        return {}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-upstash-store", action="store_true")
    ap.add_argument("--from-json", type=str, default=None)
    ap.add_argument("--from-bridge", action="store_true")
    ap.add_argument("--reason", type=str, default="import")
    ap.add_argument("--l1", type=int, default=2000)
    ap.add_argument("--topn", type=int, default=10)
    args = ap.parse_args()

    agg = {}
    if args.from_upstash_store:
        agg = load_from_upstash_store()
    if not agg and args.from_bridge:
        agg = load_from_bridge()
    if not agg and args.from_json:
        agg = load_from_json(Path(args.from_json))
    if not agg:
        print("[ERR] Tidak ada sumber data yang ditemukan.", file=sys.stderr)
        sys.exit(1)

    # build commands
    cmds = []
    cmds.append(["DEL", "xp:bucket:senior:users"])
    if args.reason:
        cmds.append(["DEL", "xp:bucket:reasons"])

    total = 0
    for uid, xp in agg.items():
        total += int(xp)
        cmds.append(["HSET", "xp:bucket:senior:users", str(uid), str(int(xp))])
        cmds.append(["SET", f"xp:u:{uid}", str(int(xp))])

    if args.reason:
        cmds.append(["HSET", "xp:bucket:reasons", args.reason, str(total)])

    l1 = min(total, max(0, args.l1))
    l2 = max(0, total - l1)
    detail = {
        "senior_total_xp": total,
        "levels": {"L1": l1, "L2": l2},
        "reasons": {args.reason: total} if args.reason else {},
        "top_users": sorted(
            [{"uid": str(uid), "xp": int(xp)} for uid, xp in agg.items()],
            key=lambda x: x["xp"], reverse=True
        )[:args.topn],
        "last_update": time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    cmds.append(["SET", "xp:bot:senior_total", str(total)])
    cmds.append(["SET", "xp:bot:senior_detail", json.dumps(detail, separators=(",",":"))])
    pipeline(cmds)
    print("[OK] Export selesai. total=", total)

if __name__ == "__main__":
    main()
