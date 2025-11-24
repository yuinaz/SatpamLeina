import re
import sys
from pathlib import Path

RE = re.compile(r"\[passive-learning\]\s*\+(\d+)\s*XP\s*->\s*total=(\d+)\s*level=([A-Za-z0-9_-]+)")

def scan(paths):
    if not paths:
        paths = [Path(".")]
    rows = []
    for base in paths:
        p = Path(base)
        if p.is_dir():
            for fp in p.rglob("*"):
                if not fp.is_file():
                    continue
                if fp.suffix.lower() not in {".log",".out",".txt"}:
                    continue
                try:
                    content = fp.read_text("utf-8", errors="ignore")
                except Exception:
                    continue
                for i, line in enumerate(content.splitlines(), start=1):
                    m = RE.search(line)
                    if m:
                        gain, total, level = int(m.group(1)), int(m.group(2)), m.group(3)
                        rows.append((fp.as_posix(), i, gain, total, level, line.strip()))
        else:
            fp = p
            try:
                content = fp.read_text("utf-8", errors="ignore")
            except Exception:
                content = ""
            for i, line in enumerate(content.splitlines(), start=1):
                m = RE.search(line)
                if m:
                    gain, total, level = int(m.group(1)), int(m.group(2)), m.group(3)
                    rows.append((fp.as_posix(), i, gain, total, level, line.strip()))
    rows.sort(key=lambda r: (r[0], r[1]))
    return rows

def main():
    rows = scan(sys.argv[1:])
    if not rows:
        print("No XP lines found.")
        return
    last_total = None
    resets = 0
    for (path, ln, gain, total, level, line) in rows:
        if last_total is not None and total < last_total:
            print(f"RESET? prev={last_total} now={total} at {path}:{ln} :: {line}")
            resets += 1
        last_total = total
    last = rows[-1]
    print(f"\nLast: total={last[3]} level={last[4]} at {last[0]}:{last[1]}")
    print(f"Lines: {len(rows)}, resets={resets}")

if __name__ == "__main__":
    main()
