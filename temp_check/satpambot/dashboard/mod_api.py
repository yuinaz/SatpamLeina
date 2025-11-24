import os, json, time, pathlib
from flask import Blueprint, jsonify, request, render_template

MOD_BP = Blueprint("mod_bp", __name__,
                   template_folder="templates",
                   static_folder="static",
                   static_url_path="/dashboard-extras-static")

DATA_DIR = pathlib.Path("data")
WL_FILE = DATA_DIR / "whitelist.json"
QUEUE_DIR = DATA_DIR / "ban_queue"
PROOF_DIR = DATA_DIR / "phish_proofs"

def _ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    (QUEUE_DIR / "_processed").mkdir(parents=True, exist_ok=True)
    PROOF_DIR.mkdir(parents=True, exist_ok=True)

@MOD_BP.route("/dashboard/moderation", methods=["GET"])
def moderation_page():
    return render_template("moderation.html")

@MOD_BP.route("/api/whitelist", methods=["GET","POST"])
def api_whitelist():
    _ensure_dirs()
    if WL_FILE.exists():
        try:
            data = json.loads(WL_FILE.read_text("utf-8"))
            if not isinstance(data, dict): data = {}
        except Exception:
            data = {}
    else:
        data = {}
    lst = set(data.get("list", []))

    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        add = body.get("add") or []
        rem = body.get("remove") or []
        for x in add: lst.add(str(x).strip())
        for x in rem: lst.discard(str(x).strip())
        WL_FILE.write_text(json.dumps({"list": sorted(lst)}, indent=2), encoding="utf-8")
        return jsonify({"ok": True, "list": sorted(lst)})
    return jsonify({"ok": True, "list": sorted(lst)})

@MOD_BP.route("/api/phish-report", methods=["POST"])
def api_phish_report():
    _ensure_dirs()
    f = request.files.get("image")
    user_id = (request.form.get("user_id") or "").strip()
    reason = (request.form.get("reason") or "").strip()
    if not f or not user_id:
        return jsonify({"ok": False, "error": "user_id dan image wajib"}), 400
    ts = int(time.time())
    ext = os.path.splitext(f.filename or "")[1].lower() or ".png"
    proof_path = PROOF_DIR / f"{ts}_{user_id}{ext}"
    f.save(proof_path)
    item = {
        "user_id": user_id,
        "reason": reason or "phishing evidence uploaded from dashboard",
        "proof": str(proof_path),
        "created_at": ts
    }
    (QUEUE_DIR / f"{ts}_{user_id}.json").write_text(json.dumps(item, indent=2), encoding="utf-8")
    return jsonify({"ok": True, "queued": True})

def register_mod_api(app):
    app.register_blueprint(MOD_BP)
