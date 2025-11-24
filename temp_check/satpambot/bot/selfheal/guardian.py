# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, time, asyncio, logging
from pathlib import Path

LOG = logging.getLogger(__name__)
STATE = Path("data/selfheal_state.json")
STATE.parent.mkdir(parents=True, exist_ok=True)

THRESHOLD = float(os.getenv("SELFHEAL_LLM_THRESHOLD", "0.90"))
BASE_BACKOFF = int(os.getenv("SELFHEAL_BASE_BACKOFF_SEC", "30"))
MAX_BACKOFF  = int(os.getenv("SELFHEAL_MAX_BACKOFF_SEC",  "900"))
WINDOW_SEC   = int(os.getenv("SELFHEAL_WINDOW_SEC",       "600"))
MAX_IN_WINDOW= int(os.getenv("SELFHEAL_MAX_IN_WINDOW",    "3"))

def _now(): return int(time.time())

def _load():
    if STATE.exists():
        try: return json.loads(STATE.read_text("utf-8"))
        except Exception: pass
    return {"crashes": [], "backoff": BASE_BACKOFF}

def _save(obj): STATE.write_text(json.dumps(obj, ensure_ascii=False, indent=2), "utf-8")

async def _ask_llm(provider: str, prompt: str):
    try:
        if provider == "groq":
            from satpambot.ml import groq_helper as gh  # type: ignore
            fn = getattr(gh, "get_groq_answer", None) or getattr(gh, "groq_answer", None)
            if not callable(fn): return None
            txt = await asyncio.to_thread(fn, f"[POLICY] JSON {{'approve':true/false,'confidence':0..1,'reason':'...'}} Error: {prompt}")
        else:
            from satpambot.ai.gemini_client import generate_text  # type: ignore
            txt = await asyncio.to_thread(generate_text, f"[POLICY] JSON {{'approve':true/false,'confidence':0..1,'reason':'...'}} Error: {prompt}")
    except Exception as e:
        LOG.warning("[selfheal] %s query failed: %r", provider, e); return None
    try:
        import json as _j
        obj = _j.loads(txt) if isinstance(txt, str) else txt
        return bool(obj.get("approve")), float(obj.get("confidence", 0.0)), str(obj.get("reason",""))
    except Exception:
        return None

class SelfHealGuardian:
    def __init__(self):
        self.state = _load()

    def record_crash(self):
        t = _now()
        self.state["crashes"] = [x for x in self.state.get("crashes", []) if t - x < WINDOW_SEC]
        self.state["crashes"].append(t); _save(self.state)

    def next_backoff(self) -> int:
        b = int(self.state.get("backoff", BASE_BACKOFF))
        b = min(max(BASE_BACKOFF, b * 2), MAX_BACKOFF)
        self.state["backoff"] = b; _save(self.state)
        return b

    async def approve_restart(self, err_summary: str):
        t = _now()
        self.state["crashes"] = [x for x in self.state.get("crashes", []) if t - x < WINDOW_SEC]
        if len(self.state["crashes"]) >= MAX_IN_WINDOW:
            return (False, 0.0, f"Rate-limit: >= {MAX_IN_WINDOW} crashes in {WINDOW_SEC}s")

        tasks = []
        if os.getenv("GROQ_API_KEY"):   tasks.append(_ask_llm("groq", err_summary))
        if os.getenv("GEMINI_API_KEY"): tasks.append(_ask_llm("gemini", err_summary))
        if not tasks:
            return (False, 0.0, "No LLM provider available")

        results = [r for r in await asyncio.gather(*tasks, return_exceptions=True) if isinstance(r, tuple)]
        if not results:
            return (False, 0.0, "All LLM checks failed")

        approvals = [1.0*ok for ok, _, _ in results]
        confs     = [c for _, c, _ in results]
        approve   = sum(approvals) >= max(1, len(results))
        score     = sum(confs)/len(confs) if confs else 0.0

        if approve and score >= THRESHOLD:
            return (True, score, "Quorum OK")
        return (False, score, "Quorum not met")
