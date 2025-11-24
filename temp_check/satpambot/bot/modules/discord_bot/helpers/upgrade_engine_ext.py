import os, json, time
from .rollback_store import restore_file

SNAP_FILE = os.path.join(os.path.dirname(__file__), "..","..","..","..","data","patch_snapshots.json")

def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def _read_all():
    if not os.path.exists(SNAP_FILE):
        return []
    try:
        with open(SNAP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def record_snapshot(snap: dict):
    _ensure_dir(SNAP_FILE)
    data = _read_all()
    data.append({"ts": int(time.time()), "snap": snap})
    with open(SNAP_FILE, "w", encoding="utf-8") as f:
        json.dump(data[-50:], f)

def list_snapshots(max_items: int = 15):
    data = _read_all()
    out = []
    for i, item in enumerate(data):
        snap = item.get("snap") or {}
        files = snap.get("files") or []
        out.append({"idx": i, "ts": int(item.get("ts", 0)), "file_count": len(files)})
    return list(reversed(out))[:max_items]

def last_snapshot():
    data = _read_all()
    return (data[-1]["snap"] if data else None)

def get_snapshot_by_rev_index(rev_idx: int):
    data = _read_all()
    if not data: return None
    if rev_idx < 0: rev_idx = 0
    if rev_idx >= len(data): return None
    return data[-1 - rev_idx].get("snap")

def attempt_rollback_last() -> bool:
    snap = last_snapshot()
    if not snap: return False
    return bool(restore_file(snap))

def attempt_rollback_rev(rev_idx: int) -> bool:
    snap = get_snapshot_by_rev_index(int(rev_idx))
    if not snap: return False
    return bool(restore_file(snap))
