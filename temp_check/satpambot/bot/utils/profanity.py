import os, re, logging

log = logging.getLogger(__name__)

# Minimal profanity lexicon; extend as needed
DEFAULT_WORDS = [
    r"fuck", r"shit", r"bitch", r"asshole", r"bastard",
    r"motherf\w+", r"dick", r"cunt"
]
_WORD_RE = re.compile(r"(?i)\b(" + "|".join(DEFAULT_WORDS) + r")\b")

def _filter_on(bot) -> bool:
    cfg = getattr(bot, "local_cfg", {})
    v = os.getenv("PROFANITY_FILTER", cfg.get("SAFETY", {}).get("profanity_filter", "off"))
    return str(v).lower() in ("1","true","on","yes")

def _rebel_on(bot) -> bool:
    try:
        cog = bot.get_cog("PersonaRebelToggle")
        if cog and hasattr(cog, "is_rebel"):
            return bool(cog.is_rebel())
    except Exception:
        pass
    cfg = getattr(bot, "local_cfg", {})
    return bool(cfg.get("PERSONA", {}).get("rebel_mode", False))

def _token(bot) -> str:
    if _rebel_on(bot):
        return "censored"
    cfg = getattr(bot, "local_cfg", {})
    return os.getenv("FILTERED_TOKEN", cfg.get("SAFETY", {}).get("filtered_token", "FILTERED"))

def sanitize(bot, text: str) -> str:
    if not text:
        return text
    if not _filter_on(bot):
        return text
    tok = _token(bot)
    result = _WORD_RE.sub(tok, text)
    if result != text:
        log.debug("[profanity] sanitized text")
    return result

def pick_filter_sticker(guild, bot):
    if not guild or not hasattr(guild, "stickers"):
        return None
    cfg = getattr(bot, "local_cfg", {})
    name = os.getenv("FILTER_STICKER_NAME", cfg.get("SAFETY", {}).get("sticker_on_filter_name", "")).strip()
    if not name:
        return None
    try:
        for s in getattr(guild, "stickers", []):
            if str(getattr(s, "name", "")).lower() == name.lower():
                return s
    except Exception:
        pass
    return None
