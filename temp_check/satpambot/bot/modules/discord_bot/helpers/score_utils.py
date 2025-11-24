from __future__ import annotations

import io, re, hashlib
from typing import Optional, Tuple

try:
    from PIL import Image
    import imagehash
except Exception:
    Image = None
    imagehash = None

try:
    import pytesseract  # optional
except Exception:
    pytesseract = None

KEYWORDS = [
    "nitro","gift","airdrop","steam","free","limited","bonus","reward",
    "discord-nitro","nitro-free","giveaway","claim","redeem"
]

def calc_hashes_from_bytes(b: bytes) -> Tuple[Optional[int], Optional[int]]:
    if Image is None or imagehash is None:
        return (None, None)
    try:
        with Image.open(io.BytesIO(b)) as im:
            im = im.convert("RGB")
            ph = imagehash.phash(im, hash_size=8)
            dh = imagehash.dhash(im, hash_size=8)
            return (int(str(ph), 16), int(str(dh), 16))
    except Exception:
        return (None, None)

def hamming64(a: int, b: int) -> int:
    return (a ^ b).bit_count()

def extract_text_ocr(b: bytes) -> str:
    if pytesseract is None or Image is None:
        return ""
    try:
        with Image.open(io.BytesIO(b)) as im:
            im = im.convert("L")
            return pytesseract.image_to_string(im) or ""
    except Exception:
        return ""

def contains_phish_keywords(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in KEYWORDS)

_url_re = re.compile(r'https?://[^\s)>\]]+', re.IGNORECASE)

def extract_urls(text: str) -> list[str]:
    return _url_re.findall(text or "")

BAD_TLDS = {".ru",".tk",".gq",".ml",".cf"}
SUS_WORDS = {"nitro","free","gift","steam","bonus","airdrop"}

def is_bad_url(u: str) -> bool:
    lu = u.lower()
    if any(lu.endswith(tld) for tld in BAD_TLDS):
        return True
    if any(w in lu for w in SUS_WORDS):
        return True
    return False

def simple_bytes_hash(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()
