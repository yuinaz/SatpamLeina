#!/usr/bin/env python3
import argparse, json
from lib_ladder import load_ladders, compute_senior_label
from lib_upstash import Upstash

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--xp", type=int, required=True, help="Senior XP to write into test namespace")
    args = ap.parse_args()
    up = Upstash()
    if not up.enabled:
        raise SystemExit("Upstash env missing. Set KV_BACKEND, UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN.")
    ladders = load_ladders(__file__)
    label, pct, rem = compute_senior_label(args.xp, ladders)
    status = f"{label} ({pct:.1f}%)"
    status_json = json.dumps({"label":label,"percent":pct,"remaining":rem,"senior_total":args.xp}, separators=(",",":"))
    print("Computed (sandbox):", status_json)
    res = up.pipeline([
        ["SET","test:xp:bot:senior_total", str(args.xp)],
        ["SET","test:learning:status", status],
        ["SET","test:learning:status_json", status_json],
        ["SET","test:learning:phase", label.split("-")[0]]
    ])
    print("Wrote to test:* via pipeline:", bool(res))
