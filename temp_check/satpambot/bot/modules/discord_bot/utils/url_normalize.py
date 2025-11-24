from urllib.parse import urlparse, parse_qs, unquote
def _domain(host: str) -> str:
    host=(host or '').lower().strip().rstrip('.')
    if host.startswith('www.'): host=host[4:]
    return host
def effective_url(raw: str) -> str:
    try:
        p=urlparse(raw); host=_domain(p.netloc)
        if host in ('l.facebook.com','lm.facebook.com'):
            q=parse_qs(p.query)
            if 'u' in q and q['u']: return unquote(q['u'][0])
        return raw
    except Exception:
        return raw
def extract_domain(raw: str) -> str:
    raw=effective_url(raw)
    try: return _domain(urlparse(raw).netloc)
    except Exception: return ''
def is_whitelisted(domain: str, whitelist: set[str]) -> bool:
    d=(domain or '').lower()
    for w in whitelist:
        w=(w or '').lower().strip()
        if not w: continue
        if d==w or d.endswith('.'+w): return True
    return False
