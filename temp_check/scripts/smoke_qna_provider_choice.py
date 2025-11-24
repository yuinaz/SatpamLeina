#!/usr/bin/env python3
import os
order = [s.strip().lower() for s in (os.getenv("QNA_PROVIDER_ORDER") or "gemini,groq").split(",") if s.strip()]
def has_gemini():
    for k in ("GEMINI_API_KEY","GOOGLE_API_KEY","GOOGLE_GENAI_API_KEY","GOOGLE_AI_API_KEY"):
        if os.getenv(k): return True
    return False
def pick(order):
    gem = has_gemini(); gro = bool(os.getenv("GROQ_API_KEY"))
    for p in order or ["gemini","groq"]:
        if p.startswith("gem") and gem: return "Gemini"
        if p.startswith(("groq","llama","mixtral","grok")) and gro: return "Groq"
    if gem: return "Gemini"
    if gro: return "Groq"
    return "NONE"
print("QNA_PROVIDER_ORDER =", order)
print("Gemini key present =", has_gemini())
print("GROQ_API_KEY set   =", bool(os.getenv("GROQ_API_KEY")))
print("-> primary =", pick(order))