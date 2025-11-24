from __future__ import annotations

import re
from typing import List

URL_RX = re.compile(r"https?://\S+", re.I)

def extract_urls_from_message(msg) -> List[str]:
    urls: List[str] = []
    text = getattr(msg, "content", "") or ""
    urls += URL_RX.findall(text)
    for e in getattr(msg, "embeds", []) or []:
        try:
            if e.url: urls.append(e.url)
            if getattr(e, "thumbnail", None) and e.thumbnail.url: urls.append(e.thumbnail.url)
            if getattr(e, "image", None) and e.image.url: urls.append(e.image.url)
        except Exception:
            pass
    return urls
