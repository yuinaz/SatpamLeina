import json, logging, os, pathlib, re, traceback

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

_UPPER_ENV_KEY = re.compile(r"^[A-Z0-9_]+$")
_PRESERVE_KEYS = {
    "QNA_FORCE_PROVIDER","QNA_PROVIDER_ORDER","QNA_PROVIDER_PRIORITY","QNA_PROVIDER",
    "LEINA_AI_PROVIDER_ORDER","LLM_PROVIDER_ORDER","LLM_PROVIDER",
    "GEMINI_FORCE_DISABLE","GROQ_FORCE_DISABLE",
    "QNA_ALLOW_FALLBACK","QNA_ALLOW_FALLBACK_WHEN_FORCED",
    "VISION_PROVIDER"
}

def _read_overrides_env():
    # Only read from data/config/overrides.render-free.json (env map)
    # Do NOT read runtime_env.json (reserved for other bot).
    p = (pathlib.Path.cwd() / "data" / "config" / "overrides.render-free.json")
    if not p.is_file():
        p = (pathlib.Path(__file__).parents[4] / "data" / "config" / "overrides.render-free.json")
    try:
        if p.is_file():
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            env = data.get("env", {})
            if isinstance(env, dict):
                return {k: str(v) for k, v in env.items() if isinstance(k, str) and _UPPER_ENV_KEY.match(k)}, str(p)
    except Exception:
        log.exception("[env-hybrid] failed reading %s", p)
    return {}, "<missing>"

def export_env():
    ov, path = _read_overrides_env()
    exported, preserved = 0, []
    # Precedence: SHELL (keep) > overrides.env
    for k, v in (ov or {}).items():
        if k in os.environ:
            preserved.append(k)
            continue
        os.environ[k] = v
        exported += 1
    keep = sorted(set(preserved).intersection(_PRESERVE_KEYS))
    preview = {k: os.environ.get(k) for k in ["QNA_FORCE_PROVIDER","QNA_PROVIDER_ORDER","LEINA_AI_PROVIDER_ORDER","LLM_PROVIDER_ORDER","GEMINI_FORCE_DISABLE","GROQ_FORCE_DISABLE"]}
    log.warning("[env-hybrid] source: overrides=%s", path)
    if keep:
        log.warning("[env-hybrid] preserved from shell: %s", ", ".join(keep))
    log.warning("[env-hybrid] exported=%d keys; preview=%s", exported, preview)

try:
    export_env()
except Exception:
    logging.getLogger(__name__).error("[env-hybrid] export failed: %s", traceback.format_exc())