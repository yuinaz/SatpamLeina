import os, json, logging, pathlib

log = logging.getLogger(__name__)

def _exists(p: str) -> bool:
    try:
        return p and os.path.exists(p)
    except Exception:
        return False

def _load_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning("[qna-config] failed to load %s: %r", path, e)
        return None

def _repo_root_from_pkg():
    try:
        import satpambot as _pkg
        here = pathlib.Path(_pkg.__file__).resolve()
        for up in range(1, 5):
            cand = here.parents[up]
            if _exists(os.path.join(cand, "data")):
                return str(cand)
        return str(here.parents[2])
    except Exception:
        return None

def _candidate_dirs():
    out = []
    env_dir = os.getenv("NEURO_CONFIG_DIR")
    if env_dir:
        out.append(env_dir)
    out.append("/opt/render/project/src/data/neuro-lite/config")
    out.append("data/neuro-lite/config")
    out.append("satpambot/data/neuro-lite/config")
    out.append("SatpamLeina/data/neuro-lite/config")
    out.append("G:/DiscordBot/SatpamLeina/data/neuro-lite/config")
    pkg_root = _repo_root_from_pkg()
    if pkg_root:
        out.append(os.path.join(pkg_root, "data/neuro-lite/config"))
    uniq = []
    for d in out:
        d = os.path.abspath(d)
        if d not in uniq:
            uniq.append(d)
    return uniq

def _resolve_topics_path(base_dir: str, candidate: str):
    """Resolve topics file allowing absolute or relative path."""
    if candidate:
        cand = os.path.normpath(candidate)
        # absolute path
        if os.path.isabs(cand) and _exists(cand):
            return cand
        # relative to base
        if base_dir:
            rel = os.path.normpath(os.path.join(base_dir, cand))
            if _exists(rel):
                return rel
    # fallback to known names inside base
    return _topics_path_fallback(base_dir)

def _topics_path_fallback(base_dir: str):
    if not base_dir: 
        return None
    cands = [
        os.path.join(base_dir, "qna_topics.json"),
        os.path.join(base_dir, "autolearn_topics.json"),
    ]
    for p in cands:
        if _exists(p):
            return p
    return None

def topics_path(base_dir: str, name: str):
    """Backwards compatible alias used by cogs; now supports absolute path."""
    return _resolve_topics_path(base_dir, name)

def load_qna_config():
    base_dir = None
    for d in _candidate_dirs():
        if _exists(d):
            base_dir = d
            break

    cfg = {
        "qna_channel_id": 1426571542627614772,
        "provider_order": ["groq","gemini"],
        "ask": {
            "interval_min": 7,
            "dedup_ttl_sec": 259200,
            "recent_max": 200,
            "topics_file": "qna_topics.json"
        },
        "answer": {
            "dedup_ttl_sec": 86400,
            "xp_award": 5
        }
    }

    # Load main config from neuro-lite/config if exists
    if base_dir:
        for name in ("qna_config.json", "autolearn_config.json", "autolearn.json"):
            p = os.path.join(base_dir, name)
            if _exists(p):
                data = _load_json(p)
                if isinstance(data, dict):
                    if "qna_channel_id" in data:
                        try: cfg["qna_channel_id"] = int(data["qna_channel_id"])
                        except Exception: pass
                    if "provider_order" in data and isinstance(data["provider_order"], list):
                        cfg["provider_order"] = [str(x).lower() for x in data["provider_order"] if str(x).strip()]
                    if "ask" in data and isinstance(data["ask"], dict):
                        for k in ("interval_min","dedup_ttl_sec","recent_max","topics_file"):
                            if k in data["ask"]:
                                cfg["ask"][k] = data["ask"][k]
                    if "answer" in data and isinstance(data["answer"], dict):
                        for k in ("dedup_ttl_sec","xp_award"):
                            if k in data["answer"]:
                                cfg["answer"][k] = data["answer"][k]
                break

    # ENV overrides (non-destructive)
    if os.getenv("QNA_CHANNEL_ID"):
        try: cfg["qna_channel_id"] = int(os.getenv("QNA_CHANNEL_ID"))
        except Exception: pass
    if os.getenv("QNA_PROVIDER_ORDER"):
        po = [s.strip().lower() for s in os.getenv("QNA_PROVIDER_ORDER").split(",") if s.strip()]
        if po: cfg["provider_order"] = po

    # NEW: allow absolute or explicit topics path via env QNA_TOPICS_FILE
    env_tp = os.getenv("QNA_TOPICS_FILE")
    if env_tp:
        tp = _resolve_topics_path(base_dir, env_tp)
        if tp:
            cfg["topics_path"] = tp
        else:
            log.warning("[qna-config] QNA_TOPICS_FILE provided but not found: %s", env_tp)
    else:
        # legacy behavior via ask.topics_file, but now absolute-aware
        topics_file = cfg["ask"].get("topics_file") or "qna_topics.json"
        cfg["topics_path"] = _resolve_topics_path(base_dir, topics_file)

    return cfg

def load_topics(tp_path: str):
    data = _load_json(tp_path) if tp_path else None
    if isinstance(data, dict) and data:
        return data
    return {
        "ai": [
            "Evaluasi kualitas jawaban AI: metrik apa yang praktis dipakai?",
            "Perbedaan supervised dan unsupervised learning apa?"
        ]
    }
