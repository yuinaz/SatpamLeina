from __future__ import annotations
import json, random, pathlib, os, time, urllib.request, urllib.error
from typing import Optional, Dict, Any, List, Tuple

_DATA_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "persona"
__weights_cache: Dict[str, Any] = {"ts": 0.0, "data": {}}
_WEIGHTS_KEY = os.getenv("LEINA_PERSONA_WEIGHTS_KEY", "persona:leina:tone_policy:weights")

def _load_json(name: str) -> Dict[str, Any]:
    p = _DATA_DIR / name
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def _load_persona() -> Dict[str, Any]:
    override = os.getenv("LEINA_PERSONA_FILE", "leina_lore.json")
    data = _load_json(override)
    if data: return data
    return _load_json("leina_personality_default.json") or {
        "persona":"default",
        "tones": {"friendly":{"prefixes":[""],"postfixes":[""]}}
    }

def _flatten_tones(data: Dict[str, Any]) -> Dict[str, Dict[str, List[str]]]:
    tones = data.get("tones", {})
    flat = {}
    for k,v in tones.items():
        if isinstance(v, dict) and ("prefixes" in v or "postfixes" in v):
            flat[k] = {"prefixes": v.get("prefixes") or [""], "postfixes": v.get("postfixes") or [""]}
        elif isinstance(v, dict):
            for sub, arr in v.items():
                key = f"{k}.{sub}"
                flat[key] = {"prefixes": (arr if isinstance(arr, list) else [str(arr)]), "postfixes": [""]}
    return flat

def _upstash_base() -> Optional[str]:
    return os.getenv("UPSTASH_REDIS_REST_URL")

def _upstash_auth() -> Optional[str]:
    tok = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    return f"Bearer {tok}" if tok else None

def _get_upstash(key: str) -> Optional[str]:
    base, auth = _upstash_base(), _upstash_auth()
    if not base or not auth: return None
    try:
        req = urllib.request.Request(f"{base}/get/{key}")
        req.add_header("Authorization", auth)
        with urllib.request.urlopen(req, timeout=4.0) as r:
            raw = r.read().decode("utf-8", "ignore")
            j = json.loads(raw)
            return j.get("result")
    except Exception:
        return None

def _load_weights_override(cache_ttl: float = 60.0) -> Dict[str, float]:
    now = time.time()
    if now - float(__weights_cache.get("ts", 0.0)) < cache_ttl:
        return dict(__weights_cache.get("data") or {})
    out: Dict[str, float] = {}
    raw = _get_upstash(_WEIGHTS_KEY)
    if raw:
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(data, dict):
                for k,v in data.items():
                    try: out[k] = float(v)
                    except: pass
        except Exception:
            out = {}
    __weights_cache["ts"] = now
    __weights_cache["data"] = dict(out)
    return out

def _choose_tone_auto(data: Dict[str, Any]) -> str:
    flat = _flatten_tones(data)
    if not flat:
        return "friendly"
    moods = data.get("moods") or []
    mood = random.choice(moods) if moods else None

    policy = data.get("tone_policy", {})
    base_w = {k: 1.0 for k in flat.keys()}
    for k,v in (policy.get("weights") or {}).items():
        if k in base_w:
            try: base_w[k] = float(v)
            except: pass
    if mood and "mood_tone_map" in policy and isinstance(policy["mood_tone_map"], dict):
        for k,v in (policy["mood_tone_map"].get(mood, {}) or {}).items():
            if k in base_w:
                try: base_w[k] += float(v)
                except: pass

    ov = _load_weights_override()
    for k,v in ov.items():
        if k in base_w:
            base_w[k] = float(v)

    items = [(k,w) for k,w in base_w.items() if w>0]
    if not items: items = list(base_w.items())
    total = sum(w for _,w in items) or len(items)
    r = random.random() * total
    s = 0.0
    for k,w in items:
        s += w
        if r <= s:
            return k
    return items[-1][0]

def _constraints(data: Dict[str, Any]) -> Dict[str, Any]:
    return data.get("constraints", {})

def format_message(answer: str, tone: Optional[str] = None) -> str:
    data = _load_persona()
    flat = _flatten_tones(data)
    if not flat:
        return answer

    chosen = tone
    if not chosen or chosen.lower() in ("auto","random"):
        chosen = _choose_tone_auto(data)
    if chosen not in flat:
        for k in flat.keys():
            if k.startswith(chosen):
                chosen = k; break
        if chosen not in flat:
            chosen = next(iter(flat.keys()))

    prefixes = flat[chosen].get("prefixes") or [""]
    postfixes = flat[chosen].get("postfixes") or [""]
    prefix = random.choice(prefixes) if prefixes else ""
    postfix = random.choice(postfixes) if postfixes else ""

    msg = f"{prefix} {answer} {postfix}".strip()

    try:
        from .leina_lore import random_catchphrase, apply_glitch, _load_json as _load_json_lore
        cons = _constraints(_load_json_lore("leina_lore.json"))
        cp_prob = float(cons.get("append_catchphrase_prob", 0.30))
        if random.random() < cp_prob:
            cp = random_catchphrase()
            if cp:
                msg = f"{msg} {cp}".strip()
        msg = apply_glitch(msg)
    except Exception:
        pass

    try:
        cons = _constraints(data)
        mx = int(cons.get("max_length", 1800))
        if len(msg) > mx:
            msg = msg[:mx-3] + "..."
    except Exception:
        pass

    return msg