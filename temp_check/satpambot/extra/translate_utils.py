from __future__ import annotations

import logging
from typing import Optional, Tuple

# Primary: googletrans-py (modern fork, httpx>=0.22)
try:
    from googletrans import Translator  # type: ignore
    _HAS_GT = True
except Exception as e:  # pragma: no cover
    _HAS_GT = False

# Fallbacks
try:
    from deep_translator import GoogleTranslator, MyMemoryTranslator  # type: ignore
    _HAS_DT = True
except Exception:
    _HAS_DT = False

try:
    from langdetect import detect as _detect_lang  # type: ignore
    _HAS_DETECT = True
except Exception:  # pragma: no cover
    _HAS_DETECT = False

log = logging.getLogger(__name__)

LANG_ALIASES = {
    "id": "id", "ind": "id", "ina": "id", "indo": "id", "bahasa": "id",
    "en": "en", "eng": "en", "english": "en",
    "ja": "ja", "jp": "ja", "jpn": "ja", "japanese": "ja",
    "zh": "zh-cn", "cn": "zh-cn", "zh-cn": "zh-cn", "zh-tw": "zh-tw", "chs": "zh-cn", "cht": "zh-tw",
}

def norm_lang(code: str, default: str = "en") -> str:
    if not code:
        return default
    c = code.strip().lower()
    return LANG_ALIASES.get(c, c)

def detect_language(text: str, default: str = "auto") -> str:
    if not text:
        return default
    if _HAS_DETECT:
        try:
            return _detect_lang(text)
        except Exception:
            pass
    # googletrans can detect if available
    if _HAS_GT:
        try:
            det = Translator().detect(text)
            if det and getattr(det, "lang", None):
                return det.lang
        except Exception:
            pass
    return default

def _gt_translate(text: str, dest: str, src: Optional[str]) -> Optional[str]:
    if not _HAS_GT:
        return None
    try:
        tr = Translator()
        res = tr.translate(text, dest=dest, src=src or "auto")
        return getattr(res, "text", None) or None
    except Exception as e:
        log.warning("googletrans translate failed: %r", e)
        return None

def _dt_translate(text: str, dest: str, src: Optional[str]) -> Optional[str]:
    if not _HAS_DT:
        return None
    # Try GoogleTranslator (unofficial) then MyMemory (rate-limited but useful)
    try:
        gt = GoogleTranslator(source=src or "auto", target=dest)
        return gt.translate(text)
    except Exception as e1:
        log.info("deep_translator.GoogleTranslator failed: %r", e1)
        try:
            mm = MyMemoryTranslator(source=src or "auto", target=dest)
            return mm.translate(text)
        except Exception as e2:
            log.warning("MyMemoryTranslator failed: %r", e2)
            return None

def translate_text(text: str, target: str = "id", source: Optional[str] = None) -> Tuple[str, str, str]:
    """Translate text. Returns tuple: (translated, src_lang, dest_lang)
    Uses googletrans-py if available, else deep-translator fallbacks.
    """
    dest = norm_lang(target, default="en")
    src  = norm_lang(source or "", default="auto") if source else "auto"
    # Short-circuit
    if not text or dest == src:
        return (text, src, dest)
    # Try primary then fallbacks
    out = _gt_translate(text, dest, src) or _dt_translate(text, dest, src)
    if out is None:
        # graceful degrade — just echo original
        return (text, src, dest)
    return (out, src, dest)
