
"""
Local Governor Tick
-------------------
Jalankan logika governor (phase & bridge override) **tanpa** perlu menjalankan bot Discord.

Usage (Git Bash / Windows):
    python -m scripts.governor_local_tick
    # atau verbose
    python -m scripts.governor_local_tick --verbose

Efek:
- Bila Junior 100% -> tulis data/neuro-lite/bridge_override.json => route XP ke Senior
- Update data/neuro-lite/gate_status.json:
    phase: junior -> senior_smp -> senior_sma -> senior_kuliah -> done
    (fallback: kalau tidak ada sub-block, jadi: junior -> senior -> done)
- Isi "block_progress" untuk SMP/SMA/KULIAH (rata-rata % tiap blok)

File yang dibaca/diperbarui:
- data/neuro-lite/learn_progress_junior.json
- data/neuro-lite/learn_progress_senior.json
- data/neuro-lite/gate_status.json
- data/neuro-lite/bridge_override.json
"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
from typing import Any, Dict

BASE = Path("data/neuro-lite")
LP_J = BASE / "learn_progress_junior.json"
LP_S = BASE / "learn_progress_senior.json"
GATE_STATUS = BASE / "gate_status.json"
BRIDGE_OVERRIDE = BASE / "bridge_override.json"

def _load_json(p: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return json.loads(json.dumps(default))

def _save_json(p: Path, d: Dict[str, Any]):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

def _block_done(block: Dict[str, int]) -> bool:
    if not isinstance(block, dict) or not block:
        return False
    try:
        return all(int(v) >= 100 for v in block.values())
    except Exception:
        return False

def _avg(block: Dict[str, int]) -> int:
    try:
        vals = [int(v) for v in block.values()]
        return int(round(sum(vals)/max(1, len(vals))))
    except Exception:
        return 0

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", "-v", action="store_true", help="Print detail perubahan.")
    args = ap.parse_args(argv)

    BASE.mkdir(parents=True, exist_ok=True)
    lpj = _load_json(LP_J, {"overall": 0, "TK": {}})
    lps = _load_json(LP_S, {"overall": 0})
    gs  = _load_json(GATE_STATUS, {"phase":"junior", "promotion_allowed": False, "ts": int(time.time())})

    junior_ok = int(lpj.get("overall", 0)) >= 100

    # deteksi sub-block senior (SMP/SMA/KULIAH) atau fallback (SD overall)
    smp = lps.get("SMP", {})
    sma = lps.get("SMA", {})
    kul = lps.get("KULIAH", {})
    has_sub = bool(smp or sma or kul)

    changed = False
    wrote_override = False

    # 1) auto-promote: junior -> senior*
    if junior_ok and gs.get("phase") == "junior":
        gs["phase"] = "senior_smp" if has_sub else "senior"
        gs["promotion_allowed"] = True
        gs["ts"] = int(time.time())
        _save_json(BRIDGE_OVERRIDE, {"split": {"junior": 0, "senior": 1}, "ts": int(time.time())})
        wrote_override = True
        changed = True

    # 2) sub-phase or fallback
    if has_sub:
        smp_done = _block_done(smp)
        sma_done = _block_done(sma)
        kul_done = _block_done(kul)

        if gs.get("phase") == "senior_smp" and smp_done:
            gs["phase"] = "senior_sma"; gs["ts"] = int(time.time()); changed = True
        if gs.get("phase") == "senior_sma" and sma_done:
            gs["phase"] = "senior_kuliah"; gs["ts"] = int(time.time()); changed = True
        if gs.get("phase") == "senior_kuliah" and kul_done:
            gs["phase"] = "done"; gs["ts"] = int(time.time()); changed = True
    else:
        if gs.get("phase") == "senior" and int(lps.get("overall", 0)) >= 100:
            gs["phase"] = "done"; gs["ts"] = int(time.time()); changed = True

    # block_progress
    if has_sub:
        gs["block_progress"] = {
            "SMP": _avg(smp) if smp else 0,
            "SMA": _avg(sma) if sma else 0,
            "KULIAH": _avg(kul) if kul else 0
        }

    if changed:
        _save_json(GATE_STATUS, gs)

    # summary
    summary = {
        "junior_overall": lpj.get("overall", 0),
        "senior_overall": lps.get("overall", 0),
        "phase": gs.get("phase"),
        "promotion_allowed": gs.get("promotion_allowed"),
        "wrote_bridge_override": wrote_override,
        "block_progress": gs.get("block_progress", {})
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.verbose:
        print(f"\nFiles written: {('bridge_override.json ' if wrote_override else '')}{'gate_status.json' if changed else ''}".strip())

if __name__ == "__main__":
    main()
