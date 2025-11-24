
# Smoke: demonstrate local failover w/o Upstash
import os, sys, asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts._env_hybrid_loader import export_env
export_env()

from satpambot.bot.modules.discord_bot.helpers.autofailover_local_core import monkey_patch_failover_local
monkey_patch_failover_local(int(os.getenv("QNA_PROVIDER_COOLDOWN_SEC","120")))

from satpambot.bot.modules.providers.llm_facade import ask

async def main():
    sysmsg = "Jawab singkat, aman."
    msgs = [{"role":"user","content":"Sebutkan satu provinsi di Indonesia."}]
    print("ORDER =", os.getenv("QNA_PROVIDER_ORDER"))
    print("COOLDOWN_SEC =", os.getenv("QNA_PROVIDER_COOLDOWN_SEC","120"))
    out = await ask(None, None, sysmsg, msgs, 0.2, 32)
    print("[OK1]", out[:120])
    os.environ["QNA_FORCE_FAIL"] = (os.getenv("QNA_PROVIDER_ORDER","groq,gemini").split(",")[0]).strip()
    out2 = await ask(None, None, sysmsg, msgs, 0.2, 32)
    print("[OK2 failover]", out2[:120])

if __name__ == "__main__":
    asyncio.run(main())
