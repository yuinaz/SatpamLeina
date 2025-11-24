#!/usr/bin/env python3
from lib_ladder import load_ladders, compute_senior_label, senior_boundaries

if __name__ == "__main__":
    ladders = load_ladders(__file__)
    print("Senior boundaries (cumulative): phase Sidx | start .. end (exclusive)")
    for (phase, sidx, lo, hi) in senior_boundaries(ladders):
        print(f"{phase}-S{sidx:<2d} | [{lo} .. {hi})  width={hi-lo}")
    samples = [0, 500, 1000, 1499, 1500, 3000, 9999, 10000, 25000, 60000, 82000, 120000]
    print("\nSamples:")
    for s in samples:
        label, pct, rem = compute_senior_label(s, ladders)
        print(f"{s:>6d} → {label:11s} {pct:5.1f}%  rem={rem}")
