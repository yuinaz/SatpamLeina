from __future__ import annotations
import os, json, logging
from pathlib import Path
from typing import Dict, Any, List, Tuple

log = logging.getLogger(__name__)

CLEANUP_DUPES = False
RESCAN_INTERVAL_SEC = 0

_JSON_INCLUDE_HINTS = ("local", "config", "satpambot")
_JSON_EXCLUDE_DIRS = ("/data/", "/.git/", "/__pycache__/")
_JSON_EXCLUDE_NAMES = ("package-lock.json",)

_NUMERIC_KEYS = {
  "OWNER_USER_ID", "LOG_CHANNEL_ID", "PUBLIC_REPORT_CHANNEL_ID", "PROGRESS_CHANNEL_ID",
  "GUILD_ID", "REPORT_CHANNEL_ID", "KEEPER_MESSAGE_ID", "KEEPER_THREAD_ID"
}
_BOOL_TRUE = {"1","true","yes","on"}
_BOOL_FALSE = {"0","false","no","off"}

_SECRET_KEYS = {
  "DISCORD_TOKEN": ("discord_token",),
  "GROQ_API_KEY": ("groq_api_key",),
  "OPENAI_API_KEY": ("openai_api_key",),
  "SERPAPI_KEY": ("serpapi_key",),
  "SERPER_API_KEY": ("serper_api_key",),
}

def _project_root() -> Path:
    here = Path(__file__).resolve()
    return here.parents[2] if len(here.parents) >= 3 else here.parent

def _iter_json_candidates(root: Path) -> List[Path]:
    out: List[Path] = []
    for p in root.rglob("*.json"):
        rel = p.relative_to(root).as_posix().lower()
        if any(x in rel for x in _JSON_EXCLUDE_DIRS):
            continue
        if p.name in _JSON_EXCLUDE_NAMES:
            continue
        name = p.name.lower()
        if any(h in name for h in _JSON_INCLUDE_HINTS) or "/config/" in rel or "/satpambot/config/" in rel:
            out.append(p)
    return out

def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def _merge_dict(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a)
    for k, v in (b or {}).items():
        out[k] = v
    return out

def _coerce_value(key: str, val):
    if isinstance(val, str):
        s = val.strip()
        if key in _NUMERIC_KEYS or key.endswith("_ID"):
            try:
                return int(s)
            except Exception:
                return s
        if s.lower() in _BOOL_TRUE:
            return True
        if s.lower() in _BOOL_FALSE:
            return False
    return val

def _overlay_env(cfg: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(cfg)
    env_map = {k: os.environ.get(k) for k in os.environ.keys()}
    out["env"] = env_map
    secrets = dict(out.get("secrets") or {})
    for env_key, aliases in _SECRET_KEYS.items():
        v = os.environ.get(env_key) or os.environ.get(env_key.lower()) or os.environ.get(env_key.upper())
        if v:
            for alias in aliases:
                secrets[alias] = v
    out["secrets"] = secrets
    for k, v in list(os.environ.items()):
        if k.startswith("RENDER_"):
            continue
        if k in _NUMERIC_KEYS or k.endswith("_ID") or k in ("NEURO_GOVERNOR_ENABLE","SELFHEAL_ENABLE"):
            out[k] = _coerce_value(k, v)
        if k in ("CHAT_ENABLE","CHAT_ALLOW_DM","CHAT_ALLOW_GUILD","CHAT_MENTIONS_ONLY","SELFHEAL_DRY_RUN"):
            out[k] = _coerce_value(k, v)
        if k in ("SEARCH_OWNER_ONLY","SEARCH_MAX_RESULTS","SEARCH_PROVIDER","GROQ_MODEL"):
            out[k] = _coerce_value(k, v)
    return out

def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    txt = json.dumps(data, ensure_ascii=False, indent=2)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(txt, encoding="utf-8")
    tmp.replace(path)

def _cleanup_duplicates(root: Path, keep: Path, candidates: List[Path]):
    removed = []
    for p in candidates:
        if p.resolve() == keep.resolve():
            continue
        rel = p.relative_to(root).as_posix()
        if "/data/" in rel:
            continue
        try:
            p.unlink()
            removed.append(rel)
        except Exception:
            pass
    return removed

def unify_env_and_json_to_local(cleanup: bool = CLEANUP_DUPES):
    root = _project_root()
    local_path = root / "local.json"
    cands = _iter_json_candidates(root)
    cands_sorted = sorted(cands, key=lambda p: (p.as_posix() != local_path.as_posix(), p.as_posix()))
    merged = {}
    for p in cands_sorted:
        data = _load_json(p)
        if isinstance(data, dict):
            merged = _merge_dict(merged, data)
    merged2 = _overlay_env(merged)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(local_path, merged2)
    removed = _cleanup_duplicates(root, local_path, cands) if cleanup else []
    log.info("[auto_local_sync] wrote %s (keys=%d) removed=%s", local_path, len(merged2.keys()), removed)
    return local_path, merged2, removed
