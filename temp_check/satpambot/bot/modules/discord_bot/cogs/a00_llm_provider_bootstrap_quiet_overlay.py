from discord.ext import commands
import os, logging, json

import asyncio

log = logging.getLogger(__name__)

# Lazy httpx import to avoid hard dep locally; Render has it.
try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEM_URL  = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

async def _ask_groq(prompt: str, model: str):
    if httpx is None: raise RuntimeError("httpx missing")
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        raise RuntimeError("GROQ_API_KEY missing")
    payload = {"model": model or os.getenv("GROQ_MODEL","llama-3.1-8b-instant"),
               "messages":[{"role":"user","content":prompt}]}
    headers = {"Authorization": f"Bearer {key}", "Content-Type":"application/json"}
    async with httpx.AsyncClient(timeout=20.0) as x:
        r = await x.post(GROQ_URL, headers=headers, json=payload)
        r.raise_for_status()
        j = r.json()
        return j["choices"][0]["message"]["content"]

async def _ask_gemini(prompt: str, model: str):
    if httpx is None: raise RuntimeError("httpx missing")
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY","")
    if not key:
        raise RuntimeError("GEMINI_API_KEY/GOOGLE_API_KEY missing")
    model = model or os.getenv("GEMINI_MODEL","gemini-2.5-flash-lite")
    url = GEM_URL.format(model=model) + f"?key={key}"
    payload = {"contents":[{"role":"user","parts":[{"text":prompt}]}]}
    headers = {"Content-Type":"application/json"}
    async with httpx.AsyncClient(timeout=20.0) as x:
        r = await x.post(url, headers=headers, json=payload)
        r.raise_for_status()
        j = r.json()
        return j["candidates"][0]["content"]["parts"][0]["text"]

async def ask(prompt: str, prefer: str = "groq", model: str = "") -> str:
    """Unified ask used by overlays. prefer in {'groq','gemini'}."""
    last_err = None
    order = ["groq","gemini"] if prefer.lower()=="groq" else ["gemini","groq"]
    for prov in order:
        try:
            if prov == "groq":
                return await _ask_groq(prompt, model)
            else:
                return await _ask_gemini(prompt, model)
        except Exception as e:
            last_err = e
            log.warning("[llm-bootstrap] %s failed: %s", prov, e)
    raise RuntimeError(f"All providers failed: {last_err}")

class LlmBootstrap(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # expose on bot
        if not hasattr(bot, "llm_ask"):
            bot.llm_ask = ask
            log.info("[llm-bootstrap] bot.llm_ask ready")
        # try export module-level ask for compat imports
        try:
            import importlib, types, sys
            mod = importlib.import_module("satpambot.bot.llm_providers")
            setattr(mod, "ask", ask)
            sys.modules["satpambot.bot.llm_providers"] = mod
            log.info("[llm-bootstrap] satpambot.bot.llm_providers.ask exported")
        except Exception as e:
            log.warning("[llm-bootstrap] compat export failed (non-fatal): %s", e)
async def setup(bot):
    await bot.add_cog(LlmBootstrap(bot))