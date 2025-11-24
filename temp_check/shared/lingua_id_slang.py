# satpambot/shared/lingua_id_slang.py
import re
from typing import Tuple

# Quick-and-dirty heuristic lists (expand anytime).
_ABBR = [
    r"\bgk\b", r"\bga\b", r"\bg\b", r"\bngg?ak\b", r"\btd\b", r"\bskr?g\b", r"\bdr\b", r"\bgpp\b",
    r"\bjd\b", r"\bjg\b", r"\bttp\b", r"\bsm\b", r"\bkrn\b", r"\bdgn\b", r"\btp\b", r"\bpls\b",
    r"\bbgt\b", r"\bbnyk\b", r"\byg\b", r"\baja\b", r"\bkmrn\b", r"\bkm\b", r"\btrs\b",
    r"\bntr\b", r"\bbrp\b", r"\bajg\b", r"\banj\b", r"\bwkwk+\b", r"\bwk\b", r"\blah\b", r"\bkok\b", r"\bsih\b",
    r"\bgue\b", r"\bgua\b", r"\blu\b", r"\blo\b", r"\bcuy\b", r"\bgan\b", r"\bmin\b", r"\bbang\b",
    r"\bkak\b", r"\bmas\b", r"\bmbak\b", r"\bmantul\b", r"\bmager\b", r"\bgabut\b", r"\bhalu\b",
]
# Common Indonesian functional words
_FUNC = [r"\byang\b", r"\bdan\b", r"\batau\b", r"\bdi\b", r"\bke\b", r"\bdari\b", r"\buntuk\b", r"\bpada\b", r"\bapa\b", r"\bkenapa\b", r"\bngapa\b", r"\bbagaimana\b"]

_ABBR_RE = re.compile("|".join(_ABBR), re.IGNORECASE)
_FUNC_RE = re.compile("|".join(_FUNC), re.IGNORECASE)

def score_indonesian_coverage(text: str) -> Tuple[float, float]:
    """Return (slang_score, func_score) normalized to [0,1] based on token counts found."""
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    if not tokens:
        return 0.0, 0.0
    slang_hits = len([t for t in tokens if _ABBR_RE.search(t)])
    func_hits = len([t for t in tokens if _FUNC_RE.search(t)])
    n = max(1, len(tokens))
    return slang_hits / n, func_hits / n

def is_mostly_indonesian(text: str) -> bool:
    slang, func = score_indonesian_coverage(text)
    return (slang + func) >= 0.25  # heuristic threshold
