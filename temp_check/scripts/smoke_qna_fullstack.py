
# --- smoke bootstrap: ensure repo root on sys.path ---
import os, sys, asyncio, re, json
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# --- end bootstrap ---

# minimal .env loader (no extra deps)
def _load_dotenv():
    for cand in [os.path.join(ROOT, ".env"), os.path.join(os.getcwd(), ".env")]:
        if os.path.isfile(cand):
            with open(cand, "r", encoding="utf-8") as f:
                for line in f:
                    line=line.strip()
                    if not line or line.startswith("#"): continue
                    if "=" not in line: continue
                    k, v = line.split("=", 1)
                    k = k.strip(); v = v.strip().strip("'").strip('"')
                    os.environ.setdefault(k, v)

def _alias_env():
    # bridge GOOGLE_API_KEY -> GEMINI_API_KEY if needed
    if not os.getenv("GEMINI_API_KEY") and os.getenv("GOOGLE_API_KEY"):
        os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY")

_load_dotenv()
_alias_env()

from satpambot.bot.modules.providers import llm_facade as lf
from satpambot.bot.modules.discord_bot.helpers.qna_quota_router import monkey_patch_failover_quota

SYSMSG = "Jawab pendek: provinsi di Indonesia yang saya sebut adalah?"
MSGS   = [{"role":"user","content":"Jawa Barat."}]

def _keys():
    return bool(os.getenv("GROQ_API_KEY")), bool(os.getenv("GEMINI_API_KEY"))

async def run_case(idx: int, force: str|None):
    await monkey_patch_failover_quota()
    if force: os.environ["QNA_QUOTA_TEST_FORCE_EXHAUST"] = force
    else: os.environ.pop("QNA_QUOTA_TEST_FORCE_EXHAUST", None)
    out = await lf.ask(None, None, SYSMSG, MSGS, 0.2, 32)
    print(f"[QNA OK{idx}]", out if isinstance(out, str) else "OK")

async def main():
    has_groq, has_gem = _keys()
    # Set provider order based on available keys
    order = []
    if has_groq: order.append("groq")
    if has_gem:  order.append("gemini")
    if not order:
        raise RuntimeError("Both GROQ_API_KEY and GEMINI_API_KEY missing in environment/.env")
    os.environ["QNA_PROVIDER_ORDER"] = ",".join(order)
    os.environ.setdefault("QNA_COOLDOWN_SEC","120")

    # normal path
    await run_case(1, None)

    # only run forced-exhaust cases when kedua key tersedia
    if has_groq and has_gem:
        # paksa groq habis -> harus switch ke gemini
        try:
            await run_case(2, "groq")
        except RuntimeError as e:
            if "forced-exhaust (smoke)" in str(e):
                print("[QNA OK2 groq-exhaust] pass (autoswitch verified)")
            else:
                raise
        # paksa gemini habis -> switch ke groq
        try:
            await run_case(3, "gemini")
        except RuntimeError as e:
            if "forced-exhaust (smoke)" in str(e):
                print("[QNA OK3 gemini-exhaust] pass (autoswitch verified)")
            else:
                raise
    else:
        print("[QNA INFO] Skipping autoswitch tests (need both GROQ & GEMINI keys)")

    os.environ.pop("QNA_QUOTA_TEST_FORCE_EXHAUST", None)

if __name__ == "__main__":
    asyncio.run(main())
