import os, io
from typing import List
try:
    from PIL import Image, ImageOps, ImageEnhance
except Exception:
    Image = None
try:
    import pytesseract
except Exception:
    pytesseract = None

DEFAULT_LANG = os.getenv("OCR_LANG", "eng+ind")
SCAM_DEFAULT_WORDS: List[str] = [
    "mrbeast", "mr beast", "$2500", "2500", "win 2500", "usd 2500",
    "free nitro", "nitro free", "bonus", "promo code", "register", "claim",
    "casino", "slots", "usdt", "trx", "withdrawal", "withdraw", "deposit",
    "airdrop", "binance", "okx", "bybit", "kucoin", "gift", "reward", "free reward"
]

def _load_ocr_words() -> List[str]:
    words = [kw.strip().lower() for kw in os.getenv("OCR_BLOCKWORDS","").split(",") if kw.strip()]
    try:
        import json
        with open("config/ocr.json","r",encoding="utf-8") as f:
            arr = (json.load(f) or {}).get("blockwords") or []
            for w in arr:
                if isinstance(w,str):
                    w=w.strip().lower()
                    if w and w not in words:
                        words.append(w)
    except Exception:
        pass
    return words

USE_SCAM_WORDS = (os.getenv("OCR_SCAM_STRICT","true").lower()=="true")
PROHIBITED_KEYWORDS: List[str] = list(dict.fromkeys(_load_ocr_words() + (SCAM_DEFAULT_WORDS if USE_SCAM_WORDS else [])))

def _preprocess(img):
    try:
        img = ImageOps.grayscale(img)
        img = ImageEnhance.Contrast(img).enhance(1.6)
        return img
    except Exception:
        return img

def extract_text(image_bytes: bytes) -> str:
    if pytesseract is None:
        return ""
    try:
        from PIL import Image as PILImage
        img = PILImage.open(io.BytesIO(image_bytes))
        img = _preprocess(img)
        txt = pytesseract.image_to_string(img, lang=DEFAULT_LANG) or ""
        return txt
    except Exception:
        return ""

def has_prohibited(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(k in t for k in PROHIBITED_KEYWORDS)
