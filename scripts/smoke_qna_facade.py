
import os, sys, asyncio
from pathlib import Path

# ensure repo root is on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# env hybrid
from scripts._env_hybrid_loader import export_env
env = export_env()

print("== LLM FACADE SMOKE ==")
print("[env] QNA_PROVIDER_ORDER =", os.getenv("QNA_PROVIDER_ORDER"))
print("[env] GROQ_MODEL =", os.getenv("GROQ_MODEL"))
print("[env] GEMINI_MODEL =", os.getenv("GEMINI_MODEL"))
print("[env] GROQ_API_KEY? ", bool(os.getenv("GROQ_API_KEY")))
print("[env] GEMINI_API_KEY?", bool(os.getenv("GEMINI_API_KEY")))

from satpambot.bot.modules.providers.llm_facade import ask

async def main():
    sysmsg = "Jawab singkat dan aman."
    msgs = [{"role":"user","content":"Sebutkan satu pulau di Indonesia."}]
    order = [s.strip() for s in (os.getenv("QNA_PROVIDER_ORDER","groq,gemini")).split(",") if s.strip()]
    for prov in order:
        model = os.getenv("GROQ_MODEL") if prov=="groq" else os.getenv("GEMINI_MODEL")
        try:
            out = await ask(prov, model, sysmsg, msgs, temperature=0.2, max_tokens=32)
            print(f"[OK] {prov} ->", (out or "")[:120])
        except Exception as e:
            print(f"[FAIL] {prov} -> {e!r}")

if __name__ == "__main__":
    asyncio.run(main())
