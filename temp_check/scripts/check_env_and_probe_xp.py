#!/usr/bin/env python3
# (see previous cell for full docstring)
import os, sys, json
from pathlib import Path

REQ_ENVS = [
    "UPSTASH_REDIS_REST_URL",
    "UPSTASH_REDIS_REST_TOKEN",
    "LEINA_PERSONA_FILE",
    "LEINA_PERSONA_WEIGHTS_KEY",
    "XP_AUTOHEAL_MODE",
    "LEARNING_ALLOW_DOWNGRADE",
]

def _ensure_repo_on_sys_path() -> None:
    here = Path(__file__).resolve()
    for parent in [here.parent] + list(here.parents):
        if (parent / "satpambot").is_dir():
            if str(parent) not in sys.path:
                sys.path.insert(0, str(parent))
            return
    fallback = here.parent.parent
    if str(fallback) not in sys.path:
        sys.path.insert(0, str(fallback))

def check_env() -> dict:
    cfg = {k: os.getenv(k) for k in REQ_ENVS}
    missing = [k for k,v in cfg.items() if not v]
    return {"env": cfg, "missing": missing}

def probe_xp() -> dict:
    _ensure_repo_on_sys_path()
    try:
        from satpambot.bot.modules.discord_bot.helpers.xp_total_resolver import stage_from_total
    except Exception as e:
        return {"ok": False, "error": f"import resolver failed: {e!r}"}
    tests = [263545, 307730, 182000, 278500, 262500, 19000]
    out = {}
    try:
        for t in tests:
            lbl, pct, meta = stage_from_total(t)
            out[str(t)] = {"label": lbl, "percent": pct, "meta": meta}
        return {"ok": True, "cases": out}
    except Exception as e:
        return {"ok": False, "error": f"probe failed: {e!r}"}

def main() -> int:
    res_env = check_env()
    res_probe = probe_xp()
    print(json.dumps({"ENV": res_env, "XP": res_probe}, indent=2))
    if res_env["missing"]:
        return 2
    if not res_probe.get("ok"):
        return 3
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
