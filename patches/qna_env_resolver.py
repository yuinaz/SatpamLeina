import os

TRUE = {"1","true","yes","on","y","t"}

def _flag(name, default=False):
    v = os.getenv(name, None)
    if v is None: return default
    return str(v).strip().lower() in TRUE

def _str(name, default=""):
    v = os.getenv(name, None)
    return str(v) if v is not None else default

def _first_nonempty(*vals):
    for v in vals:
        if v and str(v).strip():
            return str(v).strip()
    return ""

def select_qna_provider():
    forced = _str("QNA_FORCE_PROVIDER","").strip().lower()
    if forced in ("groq","gemini"): 
        return forced, "forced"
    disable_gem = _flag("GEMINI_FORCE_DISABLE", False)
    disable_groq = _flag("GROQ_FORCE_DISABLE", False)
    order = _first_nonempty(
        _str("QNA_PROVIDER_ORDER",""),
        _str("QNA_PROVIDER_PRIORITY",""),
        _str("QNA_PROVIDER",""),
        _str("LEINA_AI_PROVIDER_ORDER",""),
        _str("LLM_PROVIDER_ORDER",""),
        _str("LLM_PROVIDER",""),
    )
    if not order:
        order = "groq,gemini"
    for p in [x.strip().lower() for x in order.replace("|",",").split(",") if x.strip()]:
        if p == "groq" and not disable_groq: return "groq", "order"
        if p == "gemini" and not disable_gem: return "gemini", "order"
    if not disable_groq: return "groq", "default"
    if not disable_gem: return "gemini", "default"
    return "groq", "emergency"