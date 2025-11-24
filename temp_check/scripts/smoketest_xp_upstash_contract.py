#!/usr/bin/env python3
import os, json, sys
from satpambot.shared.xp_store import XpStore

def main():
    if not os.getenv("UPSTASH_REDIS_REST_URL") or not os.getenv("UPSTASH_REDIS_REST_TOKEN"):
        print("[SKIP] UPSTASH env not set; skipping XP contract smoketest")
        return 0
    xs = XpStore()
    kul = xs.get_ladder_kuliah()
    mag = xs.get_ladder_magang()
    sen = xs.get_senior_total()
    assert isinstance(kul, dict) and all(k.startswith("S") for k in kul.keys()), "KULIAH mapping invalid"
    assert isinstance(mag, dict) and len(mag) >= 1, "MAGANG mapping empty"
    assert isinstance(sen, int) and sen >= 0, "senior_total_v2 invalid"
    print("[OK] XP contract verified",
          json.dumps({"KULIAH": kul, "MAGANG": mag, "SENIOR": sen}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
