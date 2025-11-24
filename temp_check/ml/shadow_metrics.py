
import json, os, time, math
from typing import Dict, Any
from satpambot.config.compat_conf import get as cfg
from satpambot.ml import neuro_lite_memory_fix as nmem

METRIC_PATH = cfg("NEURO_SHADOW_METRIC_PATH", "data/neuro-lite/observe_metrics.json", str)

def _ensure_parent(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def _load() -> Dict[str, Any]:
    try:
        with open(METRIC_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"by_day": {}}

def _save(obj: Dict[str, Any]):
    _ensure_parent(METRIC_PATH)
    tmp = METRIC_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    os.replace(tmp, METRIC_PATH)

def today_key(ts=None):
    if ts is None:
        ts = time.time()
    lt = time.localtime(ts)
    return f"{lt.tm_year:04d}-{lt.tm_mon:02d}-{lt.tm_mday:02d}"

def bump(metric: str, amount: float = 1.0, user_id: int = None):
    obj = _load()
    day = today_key()
    day_obj = obj["by_day"].setdefault(day, {"metrics": {}, "unique_users": {}})
    if user_id is not None:
        day_obj["unique_users"][str(user_id)] = 1
    m = day_obj.setdefault("metrics", {})
    m[metric] = float(m.get(metric, 0.0)) + float(amount)
    _save(obj)

def rollup_to_progress():
    obj = _load()
    if not obj.get("by_day"):
        return nmem.load_junior()
    days = sorted(obj["by_day"].keys())[-7:]
    exposures = 0.0; uniq = set(); img = 0.0; links = 0.0; phish = 0.0; groq = 0.0
    import math
    for d in days:
        d_obj = obj["by_day"][d]
        met = d_obj.get("metrics", {})
        exposures += float(met.get("exposures_total", 0.0))
        img       += float(met.get("exposures_with_images", 0.0))
        links     += float(met.get("exposures_with_links", 0.0))
        phish     += float(met.get("exposures_in_phish_threads", 0.0))
        groq      += float(met.get("groq_queries", 0.0))
        for uid in d_obj.get("unique_users", {}).keys():
            uniq.add(uid)

    def f(x, k):
        return 100.0 * (1.0 - math.exp(-x / max(1.0, k)))

    j = nmem.load_junior()
    j["TK"]["L1"] = max(j["TK"]["L1"], round(f(exposures, 500), 2))
    j["TK"]["L2"] = max(j["TK"]["L2"], round(f(len(uniq), 80), 2))
    j["SD"]["L1"] = max(j["SD"]["L1"], round(f(img, 200), 2))
    j["SD"]["L2"] = max(j["SD"]["L2"], round(f(links, 150), 2))
    j["SD"]["L3"] = max(j["SD"]["L3"], round(f(phish, 80), 2))
    j["SD"]["L4"] = max(j["SD"]["L4"], round(f(groq, 40), 2))

    nmem.set_overall(j)
    return j
