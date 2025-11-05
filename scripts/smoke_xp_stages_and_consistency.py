
import json, os, re, sys
from _smoke_common import ensure_sys_path, load_overrides, upstash_get, discord_get_message, extract_json_from_text

root = ensure_sys_path()
doc, used = load_overrides()
env = doc.get("env", {}) if isinstance(doc, dict) else {}

def read_json_candidates(cands):
    for p in cands:
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f), p
        except Exception:
            continue
    return None, None

# -------- Locate ladder JSONs (local) ----------------------------------------
cands_stage = [
    "data/config/xp_stage_ladder.json",
    "data/config/xp_ladder.json",
    "data/config/xp_kuliah_ladder.json"
]
cands_work = [
    "data/config/xp_work_ladder.json",
    "data/config/work_ladder.json",
]
cands_governor = [
    "data/config/xp_governor_ladder.json",
    "data/config/governor_ladder.json",
]

stage, stage_path = read_json_candidates(cands_stage)
work, work_path = read_json_candidates(cands_work)
gov, gov_path = read_json_candidates(cands_governor)

print("[LADDER files]",
      "stage:" + (stage_path or "-"),
      "work:" + (work_path or "-"),
      "governor:" + (gov_path or "-"))

def _num(x, default=0):
    try:
        if isinstance(x, str) and x.strip()=="" : return default
        return int(float(x))
    except Exception:
        return default

def percent(cur, req):
    if req<=0: return 0.0
    return round((cur/req)*100.0, 2)

def snapshot_from_json(stage_doc):
    if not isinstance(stage_doc, dict):
        return None
    st = stage_doc.get("stage") if isinstance(stage_doc.get("stage"), dict) else stage_doc
    label = (st.get("label") or stage_doc.get("label") or "UNKNOWN")
    current = _num(st.get("current", st.get("xp", stage_doc.get("current", 0))))
    required = _num(st.get("required", stage_doc.get("required", 0)))
    return {"label": str(label), "current": current, "required": required, "percent": percent(current, required)}

local_snapshots = {}
if stage: local_snapshots["kuliah"] = snapshot_from_json(stage)
if work:  local_snapshots["work"]   = snapshot_from_json(work)
if gov:   local_snapshots["governor"] = snapshot_from_json(gov)

for k,v in local_snapshots.items():
    print(f"[LOCAL {k}] label={v['label']} current={v['current']} required={v['required']} percent={v['percent']}")

# -------- Upstash snapshot (optional) ----------------------------------------
upstash_values = {}
for key in ["xp:stage:label","xp:stage:current","xp:stage:required","xp:stage:percent","learning:status_json","xp:bot:senior_total"]:
    upstash_values[key] = upstash_get(key)

have_upstash = any(v is not None for v in upstash_values.values())
if have_upstash:
    print("[UPSTASH] available keys:", {k:v for k,v in upstash_values.items() if v is not None})
else:
    print("[UPSTASH] skipped (no creds)")

# -------- PINNED Discord backup (optional) -----------------------------------
def parse_embed_snapshot(msg_obj):
    # Try to extract snapshot from embed title/description/fields
    if not msg_obj: return None
    embeds = msg_obj.get("embeds") or []
    if not embeds: return None

    label = None; pct = None; cur = None; req = None
    for em in embeds:
        title = (em.get("title") or "") + "\n" + (em.get("description") or "")
        txt = title
        # fields too
        for f in (em.get("fields") or []):
            txt += "\n" + (f.get("name","")) + " " + (f.get("value",""))
        # Label e.g. "KULIAH-S1 — 0.0%"
        mlabel = re.search(r'([A-Z]+(?:-[A-Z0-9]+)*)\s*[—-]\s*', txt)
        if mlabel and not label:
            label = mlabel.group(1).strip()
        # Percent e.g. "67.5%"
        mperc = re.search(r'(\d+(?:\.\d+)?)\s*%', txt)
        if mperc and pct is None:
            pct = float(mperc.group(1))
        # Per-Level "0 / 19000 XP"
        mper = re.search(r'(?:Per-?Level|Per Level)[^\n]*?(\d+)\s*/\s*(\d+)\s*XP', txt, re.I)
        if mper and (cur is None or req is None):
            cur = int(mper.group(1))
            req = int(mper.group(2))

    # Assemble
    snap = {}
    if label: snap["label"] = label
    if pct is not None: snap["percent"] = float(pct)
    if cur is not None: snap["current"] = int(cur)
    if req is not None: snap["required"] = int(req)
    return snap if snap else None

pin_ch = os.getenv("XP_STATUS_CHANNEL_ID")
pin_msg = os.getenv("XP_STATUS_MESSAGE_ID")
pinned_snapshot = None
if pin_ch and pin_msg:
    data = discord_get_message(int(pin_ch), int(pin_msg))
    if data and isinstance(data, dict):
        content = data.get("content") or ""
        j = extract_json_from_text(content)
        if j and isinstance(j, dict):
            # j is like {"xp:stage:label":"SMP-L1", "xp:stage:current":"300", ...}
            lbl = str(j.get("xp:stage:label") or j.get("label") or "")
            cur = _num(j.get("xp:stage:current") or j.get("current") or 0)
            req = _num(j.get("xp:stage:required") or j.get("required") or 0)
            pct = float(j.get("xp:stage:percent") or j.get("percent") or percent(cur, req))
            pinned_snapshot = {"label": lbl, "current": cur, "required": req, "percent": pct}
            print("[PINNED JSON]", pinned_snapshot)
        else:
            # Try parse EMBED
            pinned_snapshot = parse_embed_snapshot(data)
            print("[PINNED EMBED]", pinned_snapshot if pinned_snapshot else "(no parse)")
    else:
        print("[PINNED] not accessible")
else:
    print("[PINNED] skipped (set XP_STATUS_CHANNEL_ID & XP_STATUS_MESSAGE_ID & DISCORD_BOT_TOKEN)")

# -------- Consistency rules --------------------------------------------------
def _approx_equal(a, b, tol=0.6):
    try:
        return abs(float(a) - float(b)) <= tol
    except Exception:
        return False

consistency_ok = True

# Choose authoritative source order: Upstash first (if present), else Pinned (if present), else Local JSON
author = None
if have_upstash:
    author = {
        "label": upstash_values.get("xp:stage:label"),
        "current": upstash_values.get("xp:stage:current"),
        "required": upstash_values.get("xp:stage:required"),
        "percent": upstash_values.get("xp:stage:percent"),
    }
    print("[AUTHOR] upstash")
elif pinned_snapshot:
    author = pinned_snapshot
    print("[AUTHOR] pinned")
elif local_snapshots.get("kuliah"):
    author = local_snapshots["kuliah"]
    print("[AUTHOR] local")
else:
    print("[AUTHOR] none -> skipping consistency")
    author = None

def compare_to_author(name, snap):
    global consistency_ok
    if not author or not snap: return
    if author.get("label") and snap.get("label"):
        if str(snap["label"]).upper() not in str(author["label"]).upper():
            print(f"[MISMATCH {name}] label:", snap["label"], "!=", author["label"]); consistency_ok = False
    for k in ("current","required","percent"):
        if author.get(k) is None or snap.get(k) is None:
            continue
        tol = 200 if k in ("current","required") else 1.0
        if not _approx_equal(snap[k], author[k], tol=tol):
            print(f"[MISMATCH {name}] {k}:", snap[k], "!=", author[k]); consistency_ok = False

# Compare local & pinned against author (whichever is chosen)
if author:
    if local_snapshots.get("kuliah"): compare_to_author("local", local_snapshots["kuliah"])
    if pinned_snapshot: compare_to_author("pinned", pinned_snapshot)

# Monotonic check if local files exist
def sanity_monotonic(a, b):
    if not a or not b: return True
    return b["required"] >= a["required"]

mono_ok = True
order = [local_snapshots.get("kuliah"), local_snapshots.get("work"), local_snapshots.get("governor")]
names = ["kuliah", "work", "governor"]
for i in range(len(order)-1):
    if not sanity_monotonic(order[i], order[i+1]):
        print(f"[SANITY] non-monotonic required: {names[i]}->{names[i+1]}")
        mono_ok = False

print("[RESULT] consistency_ok:", consistency_ok, "monotonic_ok:", mono_ok)
sys.exit(0 if (consistency_ok and mono_ok) else 2)
