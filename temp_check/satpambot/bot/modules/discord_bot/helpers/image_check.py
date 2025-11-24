# Blacklist image check with multi-hash (auto 2025-08-09T12:25:01.106184Z)
import os, json, re
from datetime import datetime
from satpambot.bot.modules.discord_bot.helpers.image_hashing import compute_all_hashes, hamming

DATA_FILE = os.getenv("BLACKLIST_IMAGE_HASHES", "data/blacklist_image_hashes.json")
PHASH_MAX = int(os.getenv("IMG_PHASH_MAX_DIST", "16"))
DHASH_MAX = int(os.getenv("IMG_DHASH_MAX_DIST", "12"))
AHASH_MAX = int(os.getenv("IMG_AHASH_MAX_DIST", "12"))
REGION_USE = os.getenv("IMG_REGION_HASH", "true").lower() == "true"
REGION_MAX_HITS = int(os.getenv("IMG_REGION_MIN_MATCH", "3"))

TXT_FILE = os.getenv("BLACKLIST_IMAGE_HASHES_TXT", "data/blacklist_image_hashes.txt")

def _load_md5_list():
    arr = []
    try:
        with open(TXT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                s=line.strip().lower()
                if s and re.fullmatch(r"[0-9a-f]{32}", s):
                    arr.append(s)
    except Exception:
        pass
    return arr

def _load_db():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_db(items):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

def add_to_blacklist(image_bytes: bytes, note: str = None, added_by: str = None):
    entry = compute_all_hashes(image_bytes)
    entry.update({"note": note or "", "added_by": added_by or "dashboard", "added_at": datetime.utcnow().isoformat() + "Z"})
    items = _load_db(); items.append(entry); _save_db(items); return entry

def _match_entry(entry, sample):
    pm = hamming(entry.get("phash",0), sample.get("phash",0)) <= PHASH_MAX
    dm = hamming(entry.get("dhash",0), sample.get("dhash",0)) <= DHASH_MAX
    am = hamming(entry.get("ahash",0), sample.get("ahash",0)) <= AHASH_MAX
    if pm or (dm and am): return True
    if REGION_USE:
        a = entry.get("regions") or []; b = sample.get("regions") or []; hits=0
        for ia, ib in zip(a,b):
            try:
                if hamming(ia,ib) <= DHASH_MAX: hits += 1
            except Exception: pass
        if hits >= REGION_MAX_HITS: return True
    return False

def is_blacklisted_image(image_bytes: bytes):
    s = compute_all_hashes(image_bytes)
    md5s = set(_load_md5_list())
    if md5s and 'md5' in s and (s['md5'] or '').lower() in md5s:
        return True
    for e in _load_db():
        if _match_entry(e, s): return True
    return False
