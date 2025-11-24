#!/usr/bin/env python3
# See README_PATCH.md for usage. This script moves duplicates/legacy into ./unused/ and writes reports.
# (Short version of the one I ran for you.)
import os, re, csv, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNUSED = ROOT / "unused"
REPORTS = ROOT / "_reports"
UNUSED.mkdir(exist_ok=True, parents=True)
REPORTS.mkdir(exist_ok=True, parents=True)

LEGACY = ["original_src","original","old","legacy","backup","bak","copy","copied","tmp","temp","unused","deprecated"]

def is_legacy(p: Path):
    s = str(p).lower()
    return any(f'/{k}/' in s or s.endswith('/'+k) for k in LEGACY)

def kind(p: Path):
    s = str(p).replace('\\','/').lower()
    if '/templates/' in s and s.endswith('.html'): return 'template'
    if '/static/' in s and any(s.endswith(ext) for ext in ['.js','.css','.svg','.png','.jpg','.jpeg','.webp']): return 'asset'
    if s.endswith('.py'): return 'python'
    return 'other'

def score(p: Path, k: str):
    s = str(p).replace('\\','/').lower()
    sc = 0
    if k=='template':
        if '/templates/' in s: sc += 2
        if '/templates/dashboard/' not in s: sc += 1
        try:
            t = p.read_text(encoding='utf-8', errors='ignore')
            if re.search(r'{%\s*extends\s+"base\.html"\s*%}', t): sc += 3
        except: pass
    elif k=='asset':
        if 'dashboard/static' in s: sc += 3
        if '/static/' in s: sc += 1
    elif k=='python':
        if any(x in s for x in ['app.py','main.py']): sc += 3
        if '/modules/' in s: sc += 2
        if not is_legacy(p): sc += 1
    else:
        sc += p.stat().st_size/1_000_000.0
    return sc

files = [p for p in ROOT.rglob('*') if p.is_file() and '_reports' not in str(p) and '/unused/' not in str(p).replace('\\','/')] 
by_name = {}
for p in files:
    by_name.setdefault(p.name, []).append(p)

moved = []
for name, lst in by_name.items():
    if len(lst) <= 1: 
        continue
    # pick best
    kinds = {p: kind(p) for p in lst}
    best = max(lst, key=lambda p: score(p, kinds[p]))
    for p in lst:
        if p == best: continue
        dst = UNUSED / p.relative_to(ROOT)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            shutil.move(str(p), str(dst))
            moved.append((str(p.relative_to(ROOT)), f"Duplicate of {name}, kept {best.relative_to(ROOT)}"))

# move remaining legacy
for p in [p for p in ROOT.rglob('*') if p.is_file()]:
    rp = str(p.relative_to(ROOT))
    if any(rp == m[0] for m in moved): 
        continue
    if is_legacy(p):
        dst = UNUSED / p.relative_to(ROOT)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(dst))
        moved.append((rp, "Legacy-like directory"))

with open(REPORTS/'moved_to_unused.csv','w',newline='',encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['rel','reason']); w.writerows(moved)

print(f'Moved {len(moved)} files to ./unused (see _reports/moved_to_unused.csv)')
