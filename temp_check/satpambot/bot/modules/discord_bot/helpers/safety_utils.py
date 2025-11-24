from __future__ import annotations

import os, re
from urllib.parse import urlparse
from typing import Iterable, List, Set

URL_RE = re.compile(r'(https?://[\w\-\.\u00A1-\uFFFF/%#?=&+~:;,@!\(\)\[\]\{\}]+)', re.I)

# from ENV
def _env_set(key: str) -> Set[str]:
    raw = os.getenv(key, "") or ""
    out: Set[str] = set()
    for part in re.split(r"[\s,;,]+", raw):
        p = part.strip().lower()
        if p:
            out.add(p)
    return out

FAST_BAD_DOMAINS = _env_set("FAST_BAD_DOMAINS")
FAST_BAD_KEYWORDS = _env_set("FAST_BAD_KEYWORDS")
LINK_WHITELIST = _env_set("LINK_WHITELIST")
FLAG_PUNY = os.getenv("LINK_FLAG_PUNYCODE","1") not in {"0","false","no"}

SHORTENERS = {
    "bit.ly","t.co","tinyurl.com","goo.gl","is.gd","buff.ly","cutt.ly","s.id","adf.ly","rebrand.ly","lnkd.in","trib.al","t.ly"
}

def extract_urls(text: str) -> List[str]:
    return [m.group(1) for m in URL_RE.finditer(text or "")]

def norm_domain(host: str) -> str:
    host = (host or "").strip().strip(".").lower()
    try:
        host = host.encode("ascii").decode("idna")
    except Exception:
        pass
    return host

def is_suspicious_domain(host: str, allowlist: Iterable[str]) -> bool:
    h = (host or "").lower()
    if not h or h in allowlist:
        return False
    # explicit denylist wins
    if h in FAST_BAD_DOMAINS:
        return True
    if FLAG_PUNY and 'xn--' in h:
        return True
    for kw in FAST_BAD_KEYWORDS:
        if kw and kw in h:
            return True
    # lightweight TLD heuristic based on FAST_BAD_DOMAINS suffixes
    for d in list(FAST_BAD_DOMAINS):
        if d.startswith(".") and h.endswith(d):
            return True
    return False
