import json, os, re
from typing import List
from satpambot.bot.modules.discord_bot.utils.url_normalize import extract_domain, is_whitelisted
_URL_RE = re.compile(r'(https?://\S+)', re.I)
def _load_whitelist() -> set:
    path=os.path.join('data','whitelist_domains.json')
    try:
        items=json.load(open(path,'r',encoding='utf-8'))
        return {str(x).strip().lower() for x in items if str(x).strip()}
    except Exception:
        return set()
def extract_urls(text: str) -> List[str]:
    if not text: return []
    return _URL_RE.findall(text)
async def should_skip_moderation(message) -> bool:
    content=getattr(message,'content','') or ''
    urls=extract_urls(content)
    if not urls: return False
    wl=_load_whitelist()
    domains=[extract_domain(u) for u in urls]
    return all(is_whitelisted(d, wl) for d in domains if d)
