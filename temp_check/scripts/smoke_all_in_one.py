#!/usr/bin/env python3
import os, sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

def run_or_skip(title: str, script_rel: str, args=None):
    print(f"== {title} ==")
    p = ROOT / script_rel
    print("->", PY, script_rel, *(args or []))
    if not p.exists():
        print(f"[skip] {script_rel} tidak ditemukan — melewati langkah ini.\n")
        return 0
    try:
        return subprocess.call([PY, str(p)] + (args or []))
    except Exception as e:
        print(f"[err] gagal menjalankan {script_rel}: {e}\n")
        return 1

def main():
    rc = 0
    rc |= run_or_skip("thread_guard_lint", "scripts/smoke_lint_thread_guard.py")
    print("\nDone. RC=", rc)
    sys.exit(rc)

if __name__ == "__main__":
    main()
