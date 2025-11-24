#!/usr/bin/env python3
# scripts/smoke_all.py
# Run smoke_cogs then smoke_lint_thread_guard, fail fast if any step fails.
import subprocess, sys

def run(cmd):
    print("->", " ".join(cmd), flush=True)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(r.returncode)

def main():
    py = sys.executable or "python"
    print("== smoke_cogs ==")
    run([py, "scripts/smoke_cogs.py"])
    print("== thread_guard_lint ==")
    run([py, "scripts/smoke_lint_thread_guard.py"])
    print("OK: smoke_cogs + lint passed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
