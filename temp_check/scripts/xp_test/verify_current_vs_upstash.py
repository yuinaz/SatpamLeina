#!/usr/bin/env python3
import json
from lib_ladder import load_ladders, compute_senior_label
from lib_upstash import Upstash

if __name__ == "__main__":
    up = Upstash()
    if not up.enabled:
        raise SystemExit("Upstash env missing. Set KV_BACKEND, UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN.")
    ladders = load_ladders(__file__)
    xp_raw = up.get("xp:bot:senior_total")
    try:
        xp = int(xp_raw) if xp_raw is not None else 0
    except Exception:
        try:
            j = json.loads(xp_raw); xp = int(j.get("overall",0))
        except Exception:
            xp = 0
    label_calc, pct_calc, rem = compute_senior_label(xp, ladders)
    lsj_raw = up.get("learning:status_json")
    label_live = None
    if lsj_raw:
        try:
            j = json.loads(lsj_raw)
            label_live = j.get("label")
        except Exception:
            label_live = None
    print(f"Upstash xp:bot:senior_total = {xp}")
    print(f"Computed from ladder        = {label_calc} ({pct_calc:.1f}%), rem={rem}")
    print(f"learning:status_json label = {label_live!r}")
    if label_live == label_calc:
        print("OK: live label matches computed ✅")
    else:
        print("DIFF: live label does not match computed ❗")
