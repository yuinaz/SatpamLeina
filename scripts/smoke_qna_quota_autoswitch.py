
# Smoke: quota-aware autoswitch + multi-key-pool (module-call version)
import os, sys, asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._env_hybrid_loader import export_env
export_env()

from satpambot.bot.modules.discord_bot.helpers.qna_quota_router import monkey_patch_failover_quota
from satpambot.bot.modules.providers import llm_facade as lf  # import the MODULE, not the symbol

async def run_one(tag=""):
    sysmsg = "Jawab ringkas, netral."
    msgs = [{"role":"user","content":"Sebut satu provinsi di Indonesia."}]
    out = await lf.ask(None, None, sysmsg, msgs, 0.2, 32)  # call through module to use patched func
    print(f"[OK {tag}]", out[:120])

async def main():
    os.environ.setdefault("QNA_PROVIDER_ORDER","groq,gemini")
    os.environ.setdefault("QNA_KEYPOOL_STRATEGY","least-used")
    # Key pool contoh: GROQ_API_KEYS="k1,k2"; GEMINI_API_KEYS="g1,g2"
    await monkey_patch_failover_quota()  # patch before any call

    await run_one("1")

    os.environ["QNA_QUOTA_TEST_FORCE_EXHAUST"] = "groq"
    await run_one("2 (groq-exhaust->gemini)")

    os.environ["QNA_QUOTA_TEST_FORCE_EXHAUST"] = "gemini"
    await run_one("3 (gemini-exhaust->groq)")

if __name__ == "__main__":
    asyncio.run(main())
