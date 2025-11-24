import os, json, base64

def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def restore_file(snapshot: dict) -> bool:
    files = (snapshot or {}).get("files") or []
    ok = False
    for item in files:
        try:
            p = item.get("path"); b = item.get("content_b64")
            if not p or not b: continue
            data = base64.b64decode(b.encode("utf-8"))
            _ensure_dir(p)
            with open(p, "wb") as f:
                f.write(data)
            ok = True
        except Exception:
            continue
    return ok
