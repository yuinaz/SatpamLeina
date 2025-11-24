# Smart URL reputation helper (auto)
import os, json, re, socket
from urllib.parse import urlparse
import idna

DATA_DIR = "data"
WL_FILE = os.getenv("WHITELIST_DOMAINS_FILE", os.path.join(DATA_DIR, "whitelist_domains.json"))
BL_FILE = os.getenv("BLACKLIST_DOMAINS_FILE", os.path.join(DATA_DIR, "blacklist_domains.json"))

CRITICAL_BRANDS = [ "discord.com", "discord.gg", "steamcommunity.com", "steampowered.com", "google.com", "youtube.com", "youtu.be", "facebook.com", "instagram.com", "tiktok.com", "twitter.com", "x.com", "roblox.com" ]

SHORTENERS = set([
    "bit.ly","tinyurl.com","t.co","goo.gl","is.gd","s.id","cutt.ly","shorturl.at","ow.ly","rebrand.ly","rb.gy","buff.ly","adf.ly"
])

def _load_list(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return list(default)

def load_whitelist():
    return set(_load_list(WL_FILE, CRITICAL_BRANDS + [
        "reddit.com","bilibili.com","github.com","gitlab.com","wikipedia.org","stackoverflow.com","medium.com","t.me","telegram.me","discordapp.com","googleusercontent.com","gstatic.com"
    ]))

def load_blacklist():
    return set(_load_list(BL_FILE, []))

def extract_urls(text: str):
    if not text: return []
    rx = re.compile(r"(https?://[\w\-\._~:/%\?#[\]@!$&'()*+,;=]+)", re.I)
    return rx.findall(text)

def normalize_domain(host: str) -> str:
    if not host: return ""
    host = host.split(":")[0].strip(".").lower()
    try:
        host = idna.decode(idna.encode(host))
    except Exception:
        pass
    if host.startswith("www."):
        host = host[4:]
    return host

def reg_domain(host: str) -> str:
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in ("co","com","net","org","ac","id","uk","jp","kr","au"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts)>=2 else host

def levenshtein(a, b):
    if a==b: return 0
    if len(a)==0: return len(b)
    if len(b)==0: return len(a)
    dp = list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        prev = dp[0]
        dp[0] = i
        for j,cb in enumerate(b,1):
            tmp = dp[j]
            dp[j] = min(dp[j]+1, dp[j-1]+1, prev + (0 if ca==cb else 1))
            prev = tmp
    return dp[-1]

def looks_typosquat(domain: str, legit: str) -> bool:
    d = reg_domain(normalize_domain(domain))
    l = reg_domain(normalize_domain(legit))
    if d == l: return False
    trans = str.maketrans("01357", "oelst")
    d2 = d.translate(trans)
    l2 = l.translate(trans)
    return levenshtein(d2, l2) <= 1 or d2.replace("-","") == l2 or d2.replace("l","1")==l2

def is_shortener(domain: str) -> bool:
    return reg_domain(domain) in SHORTENERS

def check_domain_reputation(domain: str):
    d = normalize_domain(domain)
    wl = load_whitelist()
    bl = load_blacklist()
    regd = reg_domain(d)
    if d in bl or regd in bl:
        return "black"
    if any(looks_typosquat(regd, legit) for legit in CRITICAL_BRANDS):
        if not (regd in wl or d in wl):
            return "sus"
    if d in wl or regd in wl:
        return "white"
    return "unknown"
