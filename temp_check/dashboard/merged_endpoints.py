# satpambot/dashboard/merged_endpoints.py
# Register additional endpoints WITHOUT requiring a global `app`.
# Endpoints:
#  - POST /dashboard/api/phash/upload       (file or {"url": ...} → pHash → blocklist.json)
#  - GET  /dashboard/api/banned_users       (sqlite/jsonl ban history)
#  - POST /dashboard/api/metrics-ingest     (bot pushes metrics)
#  - GET  /dashboard/api/metrics            (read metrics + host fallback)

import os, io, json, time, re, sqlite3
from datetime import datetime
from flask import request, jsonify, current_app

try:
    from PIL import Image as _PILImage
    import imagehash as _imgHash
except Exception:
    _PILImage = None
    _imgHash = None

try:
    import requests as _req
except Exception:
    _req = None

def _data_dir():
    return os.getenv("DATA_DIR") or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

def _ensure_dir(p:str) -> str:
    os.makedirs(p, exist_ok=True); return p

def _now(): return int(time.time())

def _ts_human(ts=None):
    ts = ts or _now()
    try: return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception: return str(ts)

def _compute_phash(pil):
    if pil is None: return None
    if _imgHash is not None:
        try: return str(_imgHash.phash(pil))
        except Exception: pass
    im = pil.convert("L").resize((8,8))
    px = list(im.getdata()); avg = sum(px)/len(px)
    bits = ''.join('1' if p>avg else '0' for p in px)
    return hex(int(bits,2))[2:].rjust(16, '0')

def _blocklist_file():
    return os.path.join(_data_dir(), "phish_lab", "phash_blocklist.json")

def _blocklist_read():
    f = _blocklist_file()
    if os.path.exists(f):
        try: return json.load(open(f, "r", encoding="utf-8"))
        except Exception: return []
    return []

def _blocklist_append(val):
    arr = _blocklist_read()
    if val and val not in arr:
        _ensure_dir(os.path.dirname(_blocklist_file()))
        json.dump(arr + [val], open(_blocklist_file(), "w", encoding="utf-8"), indent=2)
        return len(arr) + 1
    return len(arr)

def _bans_sqlite_rows(limit=50):
    db = os.path.join(_data_dir(), "bans.sqlite")
    if not os.path.exists(db): return []
    conn = sqlite3.connect(db); conn.row_factory = sqlite3.Row
    cur = conn.cursor(); rows = []
    try:
        tabs = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        cand = [t for t in tabs if re.search(r"ban", t, re.I)] or tabs
        for t in cand:
            cols = [r[1] for r in cur.execute(f"PRAGMA table_info({t})")]
            col_uid = next((c for c in cols if c.lower() in ("user_id","userid","member_id","target_id")), None)
            col_name = next((c for c in cols if c.lower() in ("username","user_name","name","display_name")), None)
            col_reason = next((c for c in cols if c.lower() in ("reason","ban_reason")), None)
            col_ts = next((c for c in cols if c.lower() in ("created_at","ts","timestamp","time")), None)
            col_mod = next((c for c in cols if c.lower() in ("moderator","mod","actor","staff")), None)
            if not col_uid and not col_name: continue
            order_col = col_ts or "rowid"
            q = f"SELECT {', '.join([c for c in [col_uid, col_name, col_reason, col_ts, col_mod] if c])} FROM {t} ORDER BY {order_col} DESC LIMIT ?"
            for r in cur.execute(q, (limit,)):
                d = dict(r)
                rows.append({
                    "user_id": d.get(col_uid) if col_uid else None,
                    "username": d.get(col_name) if col_name else None,
                    "reason": d.get(col_reason) if col_reason else None,
                    "time": d.get(col_ts) if col_ts else None,
                    "time_human": _ts_human(d.get(col_ts)) if col_ts else None,
                    "mod": d.get(col_mod) if col_mod else None,
                })
            if rows: break
    except Exception:
        pass
    finally:
        conn.close()
    return rows

def _bans_json_rows(limit=50):
    for name in ("ban_events.jsonl","banlog.jsonl","ban_events.json"):
        f = os.path.join(_data_dir(), name)
        if not os.path.exists(f): continue
        rows = []
        try:
            if f.endswith(".jsonl"):
                for line in open(f,"r",encoding="utf-8").readlines()[::-1]:
                    if not line.strip(): continue
                    try: j = json.loads(line)
                    except Exception: continue
                    rows.append({
                        "user_id": j.get("user_id") or j.get("uid"),
                        "username": j.get("username") or j.get("name"),
                        "reason": j.get("reason"),
                        "time": j.get("ts") or j.get("time"),
                        "time_human": _ts_human(j.get("ts") or j.get("time")),
                        "mod": j.get("moderator") or j.get("mod"),
                    })
                    if len(rows) >= limit: break
            else:
                arr = json.load(open(f,"r",encoding="utf-8"))
                for j in arr[::-1][:limit]:
                    rows.append({
                        "user_id": j.get("user_id") or j.get("uid"),
                        "username": j.get("username") or j.get("name"),
                        "reason": j.get("reason"),
                        "time": j.get("ts") or j.get("time"),
                        "time_human": _ts_human(j.get("ts") or j.get("time")),
                        "mod": j.get("moderator") or j.get("mod"),
                    })
        except Exception:
            continue
        if rows: return rows
    return []

def register_merged_endpoints(app):
    # Handlers (closures use helper fns above)
    def _phash_upload():
        try:
            raw = None; fname = None
            f = request.files.get("file")
            if f and f.filename:
                raw = f.read()
                fname = re.sub(r"[^A-Za-z0-9._-]+","_", f.filename)
            if raw is None and request.is_json:
                url = (request.json or {}).get("url","").strip()
                if url and _req is not None:
                    r = _req.get(url, timeout=10); r.raise_for_status()
                    raw = r.content; fname = "fromurl_" + str(_now()) + ".png"
            if raw is None:
                return jsonify({"ok":False, "error":"no-file-or-url"}), 400

            up_dir = _ensure_dir(os.path.join(_data_dir(), "uploads", "phish-lab"))
            pil = _PILImage.open(io.BytesIO(raw)).convert("RGBA") if _PILImage else None
            ph = _compute_phash(pil) if pil is not None else None
            dest = os.path.join(up_dir, f"{_now()}_{fname or 'image.png'}")
            if pil is not None: pil.save(dest)
            else: open(dest, "wb").write(raw)
            total = _blocklist_append(ph)
            return jsonify({"ok":True, "phash":ph, "saved":dest, "blocklist_total": total})
        except Exception as e:
            current_app.logger.exception("phash upload failed")
            return jsonify({"ok":False, "error": str(e)}), 500

    def _metrics_ingest():
        need = os.getenv("METRICS_INGEST_TOKEN","")
        got = request.headers.get("X-Token","")
        if need and need != got:
            return jsonify({"ok":False, "error":"unauthorized"}), 401
        try:
            data = request.get_json(force=True, silent=True) or {}
            f = os.path.join(_data_dir(), "live_metrics.json")
            _ensure_dir(os.path.dirname(f))
            data["ts"] = _now()
            json.dump(data, open(f,"w",encoding="utf-8"), indent=2)
            return jsonify({"ok":True})
        except Exception as e:
            current_app.logger.exception("metrics ingest failed")
            return jsonify({"ok":False, "error": str(e)}), 500

    def _metrics_get():
        f = os.path.join(_data_dir(), "live_metrics.json")
        data = {}
        if os.path.exists(f):
            try: data = json.load(open(f,"r",encoding="utf-8"))
            except Exception: data = {}
        resp = {
            "guilds": data.get("guilds") or data.get("guild_count") or 0,
            "members": data.get("members") or 0,
            "online": data.get("online") or 0,
            "channels": data.get("channels") or 0,
            "threads": data.get("threads") or 0,
            "latency_ms": data.get("latency_ms") or data.get("ping_ms") or 0,
            "ts": data.get("ts"),
        }
        try:
            import psutil
            resp["cpu_percent"] = psutil.cpu_percent(interval=0.0)
            resp["ram_mb"] = round(psutil.virtual_memory().used/1024/1024)
        except Exception:
            pass
        return jsonify(resp)

    def _banned_users():
        limit = max(1, min(200, int(request.args.get("limit", 50))))
        rows = _bans_sqlite_rows(limit) or _bans_json_rows(limit)
        return jsonify({"ok": True, "rows": rows, "source": "sqlite/json" if rows else "none"})

    # Register routes
    app.add_url_rule("/dashboard/api/phash/upload", view_func=_phash_upload, methods=["POST"])
    app.add_url_rule("/dashboard/api/metrics-ingest", view_func=_metrics_ingest, methods=["POST"])
    app.add_url_rule("/dashboard/api/metrics", view_func=_metrics_get, methods=["GET"])
    app.add_url_rule("/dashboard/api/banned_users", view_func=_banned_users, methods=["GET"])
