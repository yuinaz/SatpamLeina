# scripts/xp_rescue_seed.py
import os, json, sys
import httpx

REST_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REST_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
if not REST_URL or not REST_TOKEN:
    print("ENV UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN belum di-set", file=sys.stderr); sys.exit(1)

HEADERS = {"Authorization": f"Bearer {REST_TOKEN}"}

def upstash_array(cmd_array):
    # kirim body sebagai JSON ARRAY, bukan {"command": ...}
    r = httpx.post(REST_URL, headers=HEADERS, json=cmd_array, timeout=15.0)
    # perbaikan debug biar kelihatan kalau 400
    try:
        r.raise_for_status()
    except Exception:
        print("Status:", r.status_code, "Body:", r.text, file=sys.stderr)
        raise
    return r.json()

def set_str(key, val):
    # ["SET", key, value]
    return upstash_array(["SET", key, str(val)])

def set_json(key, obj):
    # value = string JSON
    payload = json.dumps(obj, separators=(',', ':'))
    return upstash_array(["SET", key, payload])

# --- nilai seed yang sama seperti sebelumnya ---
seed = {
    "xp:bot:tk_total": 1500,
    "xp:bottk_total": 1500,
    "xp:ladder:TK": {"L1": 1000, "L2": 500},
    "xp:ladder:SMP": {"L1": 0, "L2": 0, "L3": 0},
    "xp:ladder:SMA": {"L1": 0, "L2": 0, "L3": 0},
    "xp:ladder:KULIAH": {"S1": 0, "S2": 0, "S3": 0, "S4": 0, "S5": 0, "S6": 0, "S7": 0, "S8": 0},
    "learning:phase": "TK",
    "xp:bot:senior_total": 1,
}

# tulis
set_str("learning:phase", seed["learning:phase"])
set_str("xp:bot:tk_total", seed["xp:bot:tk_total"])
set_str("xp:bottk_total", seed["xp:bottk_total"])
set_str("xp:bot:senior_total", seed["xp:bot:senior_total"])

set_json("xp:ladder:TK", seed["xp:ladder:TK"])
set_json("xp:ladder:SMP", seed["xp:ladder:SMP"])
set_json("xp:ladder:SMA", seed["xp:ladder:SMA"])
set_json("xp:ladder:KULIAH", seed["xp:ladder:KULIAH"])

print("✅ Upstash XP store berhasil di-seed.")
