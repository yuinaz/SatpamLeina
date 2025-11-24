import json, os, time, hashlib
from pathlib import Path
from io import BytesIO
try:
    from PIL import Image
    import imagehash
except Exception:
    Image = None
    imagehash = None

DEFAULT_PATH = "data/phash/SATPAMBOT_PHASH_DB_V1.json"

def _ensure_dir(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def _atomic_write(path: Path, data: dict):
    _ensure_dir(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    tmp.replace(path)

def load_db(path: str = DEFAULT_PATH) -> dict:
    p = Path(path)
    if not p.exists():
        return {"version": "1", "items": []}
    txt = p.read_text(encoding="utf-8")
    try:
        data = json.loads(txt) if txt.strip() else {"version":"1","items":[]}
    except Exception:
        data = {"version":"1","items":[]}
    if isinstance(data, dict) and "phash" in data and "items" not in data:
        items = []
        for h in data.get("phash", []):
            items.append({"phash": str(h), "ts": 0})
        data = {"version":"1", "items": items}
    if "items" not in data:
        data["items"] = []
    return data

def save_db(db: dict, path: str = DEFAULT_PATH):
    _atomic_write(Path(path), db)

def _compute_sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def compute_phash(b: bytes) -> str:
    if Image is None or imagehash is None:
        return _compute_sha256(b)[:16]
    from PIL import Image as _Image
    im = _Image.open(BytesIO(b)).convert("RGB")
    return str(imagehash.phash(im))

def hamming(a: str, b: str) -> int:
    try:
        return imagehash.hex_to_hash(a) - imagehash.hex_to_hash(b)
    except Exception:
        x = int(a, 16); y = int(b, 16)
        return bin(x ^ y).count("1")

def upsert_item(db: dict, *, phash: str, sha256: str, channel_id: int, message_id: int, user_id: int, label: str = "unknown", meta: dict | None = None) -> tuple[dict,bool]:
    now = int(time.time())
    items = db.setdefault("items", [])
    for it in items:
        if it.get("sha256") == sha256 or it.get("phash") == phash:
            it["last_seen_ts"] = now
            it.setdefault("seen", 1)
            it["seen"] += 1
            return it, False
    it = {"phash": phash, "sha256": sha256, "channel_id": int(channel_id), "message_id": int(message_id), "user_id": int(user_id), "label": label, "ts": now, "meta": meta or {}}
    items.append(it)
    return it, True

def find_duplicates(db: dict, *, phash: str, max_distance: int = 8):
    items = db.get("items", [])
    dups = []
    for it in items:
        try:
            dist = hamming(phash, it.get("phash",""))
        except Exception:
            continue
        if dist <= max_distance:
            dups.append((dist, it))
    dups.sort(key=lambda x: x[0])
    return dups
