# Simple stats recorder (auto)
import os, json, time
PATH = os.getenv("STATS_FILE", "data/stats.json")

def _load():
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"events": []}

def _save(data):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def record(event: str, value: int = 1):
    data = _load()
    data["events"].append({"t": int(time.time()), "e": event, "v": int(value)})
    # keep recent 24h only
    cutoff = int(time.time()) - 24*3600
    data["events"] = [x for x in data["events"] if x["t"] >= cutoff]
    _save(data)

def summarize(last_seconds=3600):
    data = _load()
    now = int(time.time())
    cutoff = now - int(last_seconds)
    events = [x for x in data.get("events", []) if x["t"] >= cutoff]
    agg = {}
    for x in events:
        agg[x["e"]] = agg.get(x["e"], 0) + x["v"]
    # totals for cache rate
    vt_net = agg.get("vt_request_net", 0)
    vt_cache = agg.get("vt_request_cache", 0)
    total = vt_net + vt_cache
    cache_rate = (vt_cache / total * 100.0) if total else 0.0
    return {
        "since": cutoff,
        "vt_net": vt_net,
        "vt_cache": vt_cache,
        "vt_total": total,
        "cache_rate": cache_rate,
        "sus_actions": agg.get("url_sus_actions", 0),
        "black_actions": agg.get("url_black_actions", 0)
    }
