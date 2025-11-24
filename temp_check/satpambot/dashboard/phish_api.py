import os, json, time
from flask import Blueprint, request, jsonify
from PIL import Image
# v20: try import imagehash; fallback to Pillow-only aHash to avoid ImportError during smoketests
try:
    import imagehash as _imagehash_mod  # pip install ImageHash
    def compute_hash(_img):
        return str(_imagehash_mod.phash(_img))
except Exception:
    from PIL import Image as _Image  # ensure PIL is available
    def compute_hash(_img):
        # Simple average hash (8x8) fallback; deterministic but not as robust as phash
        g = _img.convert("L").resize((8, 8))
        px = list(g.getdata())
        avg = sum(px) / len(px) if px else 0
        bits = ''.join('1' if p > avg else '0' for p in px)
        try:
            return format(int(bits, 2), '016x')
        except Exception:
            # Edge case: if conversion fails, return zero hash of length 16
            return '0'*16


DATA_DIR = os.environ.get("SATPAMBOT_DATA_DIR", "data")
PHASH_JSON = os.path.join(DATA_DIR, "phish_phash.json")
HASH_TXT = os.environ.get("SATPAMBOT_PHASH_TXT", "blacklist_image_hashes.txt")

phish_api = Blueprint("phish_api", __name__)

def _ensure_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(PHASH_JSON):
        with open(PHASH_JSON, "w", encoding="utf-8") as f:
            json.dump({"hashes": []}, f, ensure_ascii=False)
    if not os.path.exists(HASH_TXT):
        open(HASH_TXT, "a", encoding="utf-8").close()

def _load():
    _ensure_files()
    with open(PHASH_JSON, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {"hashes": []}
    return data

def _save(data):
    with open(PHASH_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@phish_api.route("/dashboard/api/phash/list", methods=["GET"])
def phash_list():
    data = _load()
    return jsonify({"total": len(data.get("hashes", [])), "hashes": data.get("hashes", [])})

@phish_api.route("/dashboard/api/phash/upload", methods=["POST"])
def phash_upload():
    _ensure_files()
    files = []
    if request.files:
        for k in request.files:
            fs = request.files.getlist(k)
            files.extend(fs)
    if not files:
        return jsonify({"error": "no files"}), 400

    data = _load()
    known = set([h["hash"] if isinstance(h, dict) else h for h in data.get("hashes", [])])
    added, skipped = [], []

    for f in files:
        try:
            img = Image.open(f.stream).convert("RGB")
            ph = str(compute_hash(img))
            if ph in known:
                skipped.append(ph)
                continue
            item = {"hash": ph, "filename": f.filename, "ts": int(time.time())}
            data.setdefault("hashes", []).append(item)
            known.add(ph)
            added.append(item)
        except Exception:
            skipped.append(f"{f.filename or 'file'}:error")
            continue

    _save(data)

    try:
        with open(HASH_TXT, "w", encoding="utf-8") as out:
            for it in data["hashes"]:
                out.write((it["hash"] if isinstance(it, dict) else str(it)) + "\n")
    except Exception:
        pass

    return jsonify({"added": added, "skipped": skipped, "total": len(data.get("hashes", []))})

def register_phish_routes(app):
    app.register_blueprint(phish_api)
