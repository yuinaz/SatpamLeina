import os

TRUE = {"1","true","yes","on","y","t"}

def _flag(name, default=False):
    v = os.getenv(name, None)
    if v is None:
        return default
    return str(v).strip().lower() in TRUE

def _str(name, default=""):
    v = os.getenv(name, None)
    return str(v) if v is not None else default

def select_provider():
    forced = _str("QNA_FORCE_PROVIDER", "").strip().lower()
    if forced in ("groq","gemini"):
        return forced, "forced"
    disable_gem = _flag("GEMINI_FORCE_DISABLE", False)
    disable_groq = _flag("GROQ_FORCE_DISABLE", False)
    prio = _str("QNA_PROVIDER_PRIORITY", "Groq,Gemini").replace("|",",")
    for p in [p.strip().lower() for p in prio.split(",") if p.strip()]:
        if p == "gemini" and not disable_gem:
            return "gemini", "priority"
        if p == "groq" and not disable_groq:
            return "groq", "priority"
    if not disable_groq:
        return "groq", "default"
    if not disable_gem:
        return "gemini", "default"
    return "groq", "emergency"

def allow_fallback():
    forced = _str("QNA_FORCE_PROVIDER","").strip()
    if forced:
        return _flag("QNA_ALLOW_FALLBACK_WHEN_FORCED", False)
    return _flag("QNA_ALLOW_FALLBACK", True)

# --- print
print("[SMOKE-ENV] keys:")
for k in ("QNA_FORCE_PROVIDER","QNA_PROVIDER_PRIORITY","LLM_PROVIDER","GEMINI_FORCE_DISABLE","GROQ_FORCE_DISABLE","QNA_ALLOW_FALLBACK","QNA_ALLOW_FALLBACK_WHEN_FORCED"):
    print(f"  {k}={os.getenv(k)}")
provider, reason = select_provider()
print(f"[SMOKE-ENV] selected={provider} reason={reason} fallback_allowed={allow_fallback()}")