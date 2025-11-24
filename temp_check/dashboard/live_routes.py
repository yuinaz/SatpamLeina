from __future__ import annotations
import os, io, json, time
from flask import Blueprint, request, jsonify
from PIL import Image

api_bp = Blueprint("api", __name__, url_prefix="/api")

try:
    import imagehash
except Exception:
    imagehash = None

def _json_path() -> str:
    p = os.getenv("PHISH_PHASH_JSON", "phish_phash.json")
    data_dir = os.path.join(os.getcwd(), "data")
    if os.path.isdir(data_dir) and not os.path.isabs(p):
        p = os.path.join(data_dir, p)
    dirp = os.path.dirname(p)
    if dirp:
        os.makedirs(dirp, exist_ok=True)
    return p

def _load_json() -> dict:
    p = _json_path()
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except Exception: return {}
    return {}

def _save_json(d: dict) -> None:
    with open(_json_path(), "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

@api_bp.post("/phish/phash")
def add_phash():
    if not imagehash:
        return jsonify({"ok": False, "error": "imagehash/Pillow tidak tersedia"}), 503

    url = request.form.get("url")
    file = request.files.get("file")

    if not url and not file:
        return jsonify({"ok": False, "error": "Kirim file atau url"}), 400

    if url:
        import requests
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        src = url
    else:
        img = Image.open(file.stream).convert("RGB")
        src = file.filename

    h = str(imagehash.phash(img))
    data = _load_json()
    data[h] = {"source": src, "ts": int(time.time())}
    _save_json(data)

    try:
        from satpambot.bot.modules.discord_bot.helpers.image_hashing import refresh_external_phash_store  # type: ignore
        refresh_external_phash_store(_json_path())
    except Exception:
        pass

    return jsonify({"ok": True, "hash": h, "count": len(data)})

@api_bp.get("/phish/phash")
def list_phash():
    return jsonify(_load_json())

@api_bp.post("/ocr")
def ocr_image():
    url = request.form.get("url")
    file = request.files.get("file")

    if not url and not file:
        return jsonify({"ok": False, "error": "Kirim file atau url"}), 400

    if url:
        import requests
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content))
    else:
        img = Image.open(file.stream)

    text, err = None, None
    try:
        import pytesseract
        text = pytesseract.image_to_string(img)
    except Exception as e:
        err = f"pytesseract: {e}"
        try:
            import numpy as np, easyocr  # type: ignore
            reader = easyocr.Reader(["id", "en"], gpu=False)
            res = reader.readtext(np.array(img))
            text = "\n".join([x[1] for x in res])
        except Exception as e2:
            err += f" | easyocr: {e2}"

    if text is None:
        return jsonify({"ok": False, "error": err or "OCR tidak tersedia"}), 503
    return jsonify({"ok": True, "text": text})
