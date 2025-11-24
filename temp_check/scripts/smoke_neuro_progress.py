import json, sys, pathlib
root = pathlib.Path("data")
jr = root / "learn_progress_junior.json"
sr = root / "learn_progress_senior.json"
if not jr.exists():
    print("[WARN] missing", jr)
if not sr.exists():
    print("[WARN] missing", sr)
for p in (jr, sr):
    if p.exists():
        try:
            json.loads(p.read_text(encoding="utf-8"))
            print("[OK] JSON parse:", p.name)
        except Exception as e:
            print("[FAIL] bad JSON in", p.name, "::", e)
            sys.exit(1)
print("Done.")
