#!/usr/bin/env python3
import os, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def envflag(name, default=""):
    return (os.getenv(name) or default).strip()

def yesno(x): return "YES" if x else "NO"

# XP
xp_key = envflag("XP_SENIOR_KEY", "<not set>")
kv = envflag("KV_BACKEND", "<not set>")
upstash_url = "set" if envflag("UPSTASH_REST_URL") else "missing"
upstash_tok = "set" if envflag("UPSTASH_REST_TOKEN") else "missing"

# Providers
qna_order = [p.strip() for p in envflag("QNA_PROVIDER", "gemini,groq").lower().split(",") if p.strip()]
groq_key = bool(envflag("GROQ_API_KEY"))
gai_key  = bool(envflag("GEMINI_API_KEY") or envflag("GOOGLE_API_KEY"))
groq_model = envflag("GROQ_MODEL", "llama-3.1-70b-versatile")
gem_model  = envflag("GEMINI_MODEL", envflag("LLM_GEMINI_MODEL", "gemini-2.5-flash"))

print("=== Preflight: XP & QnA Providers ===")
print(f"XP_SENIOR_KEY          : {xp_key}")
print(f"KV_BACKEND             : {kv}")
print(f"UPSTASH_REST_URL/TOKEN : {upstash_url}/{upstash_tok}")
print(f"QNA_PROVIDER order     : {qna_order}")
print(f"GROQ_API_KEY present   : {yesno(groq_key)} (model={groq_model})")
print(f"GEMINI/GOOGLE key      : {yesno(gai_key)} (model={gem_model})")

# Decision the code will take for QnA primary
def pick_primary(order, has_gemini, has_groq):
    for p in order or ["gemini","groq"]:
        if p.startswith(("gemini","google","gai")) and has_gemini: return "Gemini"
        if p.startswith(("groq","llama","mixtral")) and has_groq:  return "Groq"
    # fallback
    prov = envflag("AI_PROVIDER", "auto").lower()
    if prov.startswith("gem"): return "Gemini" if has_gemini else "NONE"
    if prov.startswith("gro"): return "Groq" if has_groq else "NONE"
    return "Gemini" if has_gemini else ("Groq" if has_groq else "NONE")

primary = pick_primary(qna_order, gai_key, groq_key)
print(f"QnA primary provider   : {primary}")
if primary == "NONE":
    print("[WARN] No valid provider keys found. Set GEMINI_API_KEY/GOOGLE_API_KEY and/or GROQ_API_KEY.")
