#!/usr/bin/env python3
import argparse
from lib_ladder import load_ladders, compute_senior_label

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--xp", type=int, required=True, help="Senior XP to test")
    args = ap.parse_args()
    ladders = load_ladders(__file__)
    label, pct, rem = compute_senior_label(args.xp, ladders)
    print(f"XP={args.xp} → {label} ({pct:.1f}%), remaining={rem}")
