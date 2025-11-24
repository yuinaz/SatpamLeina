#!/usr/bin/env python3
import os, asyncio
from satpambot.helpers.llm_clients import QnaClient
async def main():
    prompt="Sebutkan 3 kebiasaan kecil yang meningkatkan produktivitas."
    system="Jawab ringkas dalam poin."
    g=QnaClient()
    print("Providers:")
    print("  GEMINI_API_KEY set?", bool(os.getenv("GEMINI_API_KEY")))
    print("  GROQ_API_KEY set?  ", bool(os.getenv("GROQ_API_KEY")))
    print("  OPENAI_BASE_URL   =", os.getenv("OPENAI_BASE_URL"))
    print("  GROQ_MODEL        =", os.getenv("GROQ_MODEL", os.getenv("LLM_GROQ_MODEL","llama-3.1-8b-instant")))
    print("  GEMINI_MODEL      =", os.getenv("GEMINI_MODEL", os.getenv("LLM_GEMINI_MODEL","gemini-1.5-flash")))
    try:
        print("\n[QnaClient priority flow]")
        ans=await g.answer(prompt, system)
        print("[QNA OK]\n", ans[:400])
    except Exception as e:
        print("[QNA ERR]", e)
if __name__=="__main__": asyncio.run(main())
