from __future__ import annotations

import os, logging
from typing import Optional
log = logging.getLogger(__name__)

# API client (optional)
try:
    import aiohttp
except Exception:
    aiohttp = None  # type: ignore

async def ocr_via_api(bytes_data: bytes, filename: str = "image.jpg") -> Optional[str]:
    url = os.getenv("OCR_API_URL", "")
    if not url or aiohttp is None:
        return None
    key = os.getenv("OCR_API_KEY","")
    timeout = float(os.getenv("OCR_API_TIMEOUT","3.5"))
    try:
        timeout = aiohttp.ClientTimeout(total=timeout)
        headers = {}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as sess:
            data = aiohttp.FormData()
            data.add_field("file", bytes_data, filename=filename, content_type="application/octet-stream")
            async with sess.post(url, data=data) as resp:
                if resp.status != 200:
                    return None
                js = await resp.json(content_type=None)
                if isinstance(js, dict):
                    if isinstance(js.get("text"), str):
                        return js["text"]
                    data_obj = js.get("data")
                    if isinstance(data_obj, dict) and isinstance(data_obj.get("text"), str):
                        return data_obj["text"]
                return None
    except Exception:
        return None

# Local OCR (pytesseract), using OCR_LANG if available
try:
    import pytesseract
    from PIL import Image
    HAVE_LOCAL = True
except Exception:
    HAVE_LOCAL = False

async def ocr_via_local(bytes_data: bytes, lang: str = "") -> Optional[str]:
    if not HAVE_LOCAL:
        return None
    try:
        from io import BytesIO
        img = Image.open(BytesIO(bytes_data)).convert("RGB")
        cfg = {}
        if lang:
            cfg["lang"] = lang
        text = pytesseract.image_to_string(img, **cfg)
        return text
    except Exception:
        return None

async def smart_ocr(bytes_data: bytes, filename: str = "image.jpg") -> Optional[str]:
    # Try API first if configured, otherwise local
    txt = await ocr_via_api(bytes_data, filename=filename)
    if txt:
        return txt
    lang = os.getenv("OCR_LANG","")
    return await ocr_via_local(bytes_data, lang=lang)
