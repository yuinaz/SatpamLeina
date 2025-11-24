
import os, time, asyncio, logging
from typing import List, Dict, Optional

log = logging.getLogger(__name__)

def _norm(v: Optional[str]) -> str:
    return (v or "").strip().lower()

def _parse_order(forced: Optional[str]) -> List[str]:
    raw = os.getenv("QNA_PROVIDER_ORDER","groq,gemini")
    order = [_norm(x) for x in raw.split(",") if x.strip()]
    order = [p for p in order if p in ("groq","gemini")]
    if not order:
        order = ["groq","gemini"]
    f = _norm(forced)
    if f and f in order:
        order = [f] + [p for p in order if p != f]
    return order

def _model_for(prov: str, model: Optional[str]) -> Optional[str]:
    if model: return model
    if prov == "groq":   return os.getenv("GROQ_MODEL","llama-3.1-8b-instant")
    if prov == "gemini": return os.getenv("GEMINI_MODEL","gemini-2.5-flash-lite")
    return model

def _is_transient(err: Exception) -> bool:
    s = str(err).lower()
    needles = ("429","rate","quota","exceeded","timeout","timed out","connect error","temporary","retry")
    return any(n in s for n in needles)

def monkey_patch_failover_local(cooldown_sec: int = 120):
    from satpambot.bot.modules.providers import llm_facade as lf  # type: ignore
    orig = lf.ask  # async function
    cooldown = {}
    lock = asyncio.Lock()

    async def wrapped(provider: str, model: Optional[str], system: str, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 320):
        order = _parse_order(provider)
        now = time.time()
        active = [p for p in order if cooldown.get(p, 0.0) <= now] or order
        last_err: Optional[Exception] = None

        force_fail = _norm(os.getenv("QNA_FORCE_FAIL"))

        for prov in active:
            use_model = _model_for(prov, model)
            try:
                if force_fail == prov:
                    raise RuntimeError("forced-fail (smoke)")
                return await orig(prov, use_model, system, messages, temperature, max_tokens)
            except Exception as e:
                last_err = e
                if _is_transient(e):
                    async with lock:
                        cooldown[prov] = time.time() + cooldown_sec
                    log.warning("[qna-failover-local] %s transient-fail -> cooldown %ss; trying next | %r", prov, cooldown_sec, e)
                    continue
                log.warning("[qna-failover-local] %s failed -> trying next | %r", prov, e)
                continue

        raise last_err if last_err else RuntimeError("all providers failed")

    lf.ask = wrapped  # type: ignore[assignment]
    log.info("[qna-failover-local] llm_facade.ask patched; cooldown_sec=%s", cooldown_sec)
