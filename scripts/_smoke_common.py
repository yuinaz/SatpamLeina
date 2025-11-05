import os, sys, json
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

def find_repo_root(start: Path) -> Path:
    p = start.resolve()
    for _ in range(14):
        if (p / "satpambot").exists() or (p / "scripts").exists():
            return p
        if (p / ".git").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    return start.resolve().parents[1]

def ensure_sys_path():
    here = Path(__file__).resolve()
    root = find_repo_root(here)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root

def _parse_dotenv(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip("'").strip('"')
        env[k] = v
    return env

def _normalize_env(e: dict) -> dict:
    if e.get("GEMINI_API_KEY") and not e.get("GOOGLE_API_KEY"):
        e["GOOGLE_API_KEY"] = e["GEMINI_API_KEY"]
    if e.get("GOOGLE_API_KEY") and not e.get("GEMINI_API_KEY"):
        e["GEMINI_API_KEY"] = e["GOOGLE_API_KEY"]
    if e.get("DISCORD_TOKEN") and not e.get("DISCORD_BOT_TOKEN"):
        e["DISCORD_BOT_TOKEN"] = e["DISCORD_TOKEN"]
    if e.get("DISCORD_BOT_TOKEN") and not e.get("DISCORD_TOKEN"):
        e["DISCORD_TOKEN"] = e["DISCORD_BOT_TOKEN"]
    if e.get("GROQ_APIKEY") and not e.get("GROQ_API_KEY"):
        e["GROQ_API_KEY"] = e["GROQ_APIKEY"]
    return e

def _export_env_map(m: dict) -> None:
    for k, v in m.items():
        if v is None or v == "":
            continue
        if os.getenv(k) is None:
            os.environ[k] = v

def _load_dotenv_fallback() -> bool:
    root = ensure_sys_path()
    candidates = [root / ".env", root / ".env.local", root / ".env.development"]
    merged = {}
    for p in candidates:
        merged.update(_parse_dotenv(p))
    if not merged:
        return False
    merged = _normalize_env(merged)
    _export_env_map(merged)
    keys = ["GROQ_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY", "DISCORD_BOT_TOKEN", "UPSTASH_REDIS_REST_URL"]
    diag = {k: ("set" if os.getenv(k) else "missing") for k in keys}
    print("[env-loader] .env fallback loaded:", diag)
    return True

def export_env_if_any() -> bool:
    try:
        from scripts._env_hybrid_loader import export_env  # type: ignore
        export_env()
        print("[env-loader] hybrid loader active")
        return True
    except Exception:
        pass
    ok = _load_dotenv_fallback()
    return ok

def load_overrides(path_candidates=None) -> Tuple[Dict[str, Any], Optional[str]]:
    if path_candidates is None:
        path_candidates = [
            "data/config/overrides.render-free.patched.json",
            "data/config/overrides.render-free.json",
            "data/config/overrides.render-qna-min.json",
        ]
    root = ensure_sys_path()
    for p in path_candidates:
        pp = Path(p)
        if not pp.is_absolute():
            pp = root / p
        if pp.exists():
            try:
                return json.loads(pp.read_text(encoding="utf-8")), str(pp)
            except Exception:
                pass
    return {}, None

def upstash_get(key: str) -> Optional[str]:
    import urllib.request, urllib.error
    url = os.getenv("UPSTASH_REDIS_REST_URL")
    tok = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if not url or not tok:
        return None
    if url.endswith("/"):
        url = url[:-1]
    req = urllib.request.Request(f"{url}/get/{key}")
    req.add_header("Authorization", f"Bearer {tok}")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read()
            data = json.loads(raw.decode("utf-8", "ignore"))
            return None if data.get("result") in (None, "null") else str(data.get("result"))
    except Exception:
        return None

def discord_get_message(channel_id: int, message_id: int) -> Optional[Dict[str, Any]]:
    import urllib.request, urllib.error
    token = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
    if not token:
        return None
    req = urllib.request.Request(f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}")
    req.add_header("Authorization", f"Bot {token}")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8", "ignore"))
    except Exception:
        return None

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    import re
    if not text:
        return None
    m = re.search(r'\{[\s\S]*\}', text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None
