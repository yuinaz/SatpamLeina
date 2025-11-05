
from __future__ import annotations
import os, time, inspect
from typing import Any

_PATCHED = False
_COOLDOWN: dict[str,float] = {}

def _now() -> float: return time.time()

def _order_from_env():
    raw = os.getenv("QNA_PROVIDER_ORDER","groq,gemini")
    out=[]; seen=set()
    for p in raw.replace(";",",").split(","):
        p=p.strip().lower()
        if p and p not in seen:
            seen.add(p); out.append(p)
    return out or ["groq","gemini"]

def _cooldown_sec() -> int:
    try: return int(os.getenv("QNA_COOLDOWN_SEC","120"))
    except Exception: return 120

def _sig(fn):
    try: return inspect.signature(fn)
    except Exception: return None

def _val_for(name: str, core: dict[str, Any]) -> tuple[bool, Any]:
    if name in ("client",): return True, core["client"]
    if name in ("model",): return True, core["model"]
    if name in ("system","sysmsg"): return True, core["sysmsg"]
    if name in ("messages","msgs"): return True, core["msgs"]
    if name in ("temp","temperature"): return True, core["temp"]
    if name in ("max_tokens","max_new_tokens"): return True, core["max_tokens"]
    if name in ("provider",): return True, core.get("provider")
    return False, None

def _build_args_by_sig(sig: inspect.Signature, core: dict[str,Any], extra: dict[str,Any] | None):
    params = sig.parameters
    has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
    has_provider_param = "provider" in params
    pos = []
    kw = {}
    used_keys = set()
    # Fill in exact signature order
    for name, p in params.items():
        ok, val = _val_for(name, core)
        if not ok:
            continue
        used_keys.add(name)
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            pos.append(val)
        elif p.kind == inspect.Parameter.KEYWORD_ONLY:
            kw[name] = val

    # If function has **kwargs (has_varkw) and NO provider param,
    # inject provider via kwargs so facades reading from **kwargs can see it.
    if (not has_provider_param) and has_varkw and (core.get("provider") is not None):
        kw["provider"] = core["provider"]

    # Merge extras: keep only non-None; don't override core; obey **kwargs availability
    if extra:
        for k, v in extra.items():
            if v is None: continue
            if k == "provider": continue  # router controls provider
            if k in used_keys: continue
            if (k in params) or has_varkw:
                kw.setdefault(k, v)

    return pos, kw, has_varkw, has_provider_param

async def _call_strict(orig, client, model, sysmsg, msgs, temp, max_tokens, provider, extra_kwargs):
    sig = _sig(orig)
    core = {"client":client,"model":model,"sysmsg":sysmsg,"msgs":msgs,"temp":temp,"max_tokens":max_tokens,"provider":provider}
    if not sig:
        kw = dict(extra_kwargs or {})
        if provider is not None: kw["provider"] = provider
        return await orig(client, model, sysmsg, msgs, temp, max_tokens, **kw)

    pos, kw, has_varkw, has_provider_param = _build_args_by_sig(sig, core, extra_kwargs or {})
    try:
        return await orig(*pos, **kw)
    except TypeError as te:
        msg = str(te).lower()
        # If provider duplication occurs, drop provider from kw and retry
        if "provider" in msg and "multiple values" in msg:
            if "provider" in kw:
                kw2 = dict(kw); kw2.pop("provider", None)
                return await orig(*pos, **kw2)
        # If unexpected keyword and no **kwargs, strip extras not in signature
        if "unexpected keyword" in msg and not has_varkw:
            allowed = set(sig.parameters.keys())
            kw3 = {k:v for k,v in kw.items() if k in allowed}
            return await orig(*pos, **kw3)
        # Last resort: remove provider entirely and call with core only
        kw4 = dict(kw); kw4.pop("provider", None)
        return await orig(*pos, **kw4)

async def _ask_failover(orig_ask, client, model, sysmsg, msgs, temp, max_tokens, kwargs):
    order = _order_from_env()
    force = (os.getenv("QNA_QUOTA_TEST_FORCE_EXHAUST","") or "").lower()
    last_err = None
    for prov in order:
        until = _COOLDOWN.get(prov, 0.0)
        if until and _now() < until:
            continue
        try:
            if force and prov.startswith(force):
                raise RuntimeError("forced-exhaust (smoke)")
            return await _call_strict(orig_ask, client, model, sysmsg, msgs, temp, max_tokens, prov, kwargs or {})
        except Exception as e:
            _COOLDOWN[prov] = _now() + _cooldown_sec()
            last_err = e
    if last_err: raise last_err
    raise RuntimeError("QNA failover: no available providers")

async def monkey_patch_failover_quota():
    global _PATCHED
    if _PATCHED: return
    from satpambot.bot.modules.providers import llm_facade as lf
    orig = lf.ask

    async def wrapper(client, model, sysmsg, msgs, temp, max_tokens, *args, **kwargs):
        # Clean provider=None from caller
        if kwargs.get("provider", None) is None:
            kwargs.pop("provider", None)
        # If caller explicitly sets provider or passes any extra positionals, pass-through
        if len(args) >= 1 or ("provider" in kwargs):
            return await orig(client, model, sysmsg, msgs, temp, max_tokens, *args, **kwargs)
        # Otherwise, route with failover
        return await _ask_failover(orig, client, model, sysmsg, msgs, temp, max_tokens, kwargs)

    lf.ask = wrapper  # type: ignore
    _PATCHED = True
