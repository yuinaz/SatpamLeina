import os, time, threading, psutil
from datetime import datetime, timezone

# Global aggregates
AGG = {
    "commands_total": 0,
    "commands_ok": 0,
    "commands_err": 0,
    "moderation": {"ban": 0, "unban": 0, "warn": 0, "timeout": 0},
}

LATEST_METRICS = {
    "cpu_percent": 0.0,
    "ram_percent": 0.0,
    "proc_mem_mb": 0.0,
    "uptime_s": 0,
}

_start_time = time.time()

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def inc(path: str, amount: int = 1):
    # path like "moderation.ban" or "commands_total"
    cur = AGG
    parts = path.split(".")
    for i, k in enumerate(parts):
        if i == len(parts)-1:
            if k not in cur:
                cur[k] = 0
            cur[k] += amount
        else:
            cur = cur.setdefault(k, {})

def set_metric(key: str, value):
    LATEST_METRICS[key] = value

def snapshot():
    return {
        "timestamp": now_iso(),
        "metrics": dict(LATEST_METRICS),
        "aggregate": dict(AGG),
    }

def start_sampler(interval_sec: int = 60):
    # Background sampler for CPU/RAM/proc
    proc = psutil.Process(os.getpid())
    def loop():
        while True:
            try:
                LATEST_METRICS["cpu_percent"] = psutil.cpu_percent(interval=None)
                LATEST_METRICS["ram_percent"] = psutil.virtual_memory().percent
                LATEST_METRICS["proc_mem_mb"] = proc.memory_info().rss / (1024*1024)
                LATEST_METRICS["uptime_s"] = int(time.time() - _start_time)
            except Exception:
                pass
            time.sleep(interval_sec)
    t = threading.Thread(target=loop, daemon=True)
    t.start()
    return t
