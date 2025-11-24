
# a00_config_hotreload_overlay.py (v7.6)
# Watches YAML config files and applies them to env + dispatches a bot event.
from discord.ext import commands
import os, asyncio, logging, json, time
from pathlib import Path
from typing import Dict, Any

log = logging.getLogger(__name__)
CONFIG_DIR = Path(os.getenv("CONFIG_DIR", "satpambot/config"))
POLL_SEC = float(os.getenv("CONFIG_POLL_SEC", "4"))
ENABLED = os.getenv("CONFIG_WATCH", "1") == "1"

def _mtime(p: Path) -> float:
    try: return p.stat().st_mtime
    except Exception: return 0.0

def _setenv(k: str, v: Any):
    if v is None: return
    os.environ[str(k)] = str(v)

def _load_yaml(p: Path) -> Any:
    import yaml
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception as e:
        log.info("[hotreload] YAML load failed for %s: %r", p, e)
        return None

def _apply_ai_yaml(data: Dict[str, Any]):
    if not isinstance(data, dict): return {}
    # map keys to env for llm_providers
    chain = (data.get("model_chain") or [])
    if isinstance(chain, list) and chain:
        # pick the first as default override (simple heuristic)
        first = chain[0]
        prov = (first.get("provider") or "").lower()
        model = first.get("model")
        if prov == "groq" and model: _setenv("LLM_GROQ_MODEL", model)
        if prov == "gemini" and model: _setenv("LLM_GEMINI_MODEL", model)
    if data.get("default_model"): _setenv("LLM_PROVIDER", data["default_model"])
    samp = data.get("sampling") or {}
    if "temperature" in samp: _setenv("LLM_TEMPERATURE", samp["temperature"])
    return {"provider": os.getenv("LLM_PROVIDER"), "groq_model": os.getenv("LLM_GROQ_MODEL"), "gemini_model": os.getenv("LLM_GEMINI_MODEL")}

def _apply_autolearn_yaml(data: Dict[str, Any]):
    if not isinstance(data, dict): return {}
    core = data.get("autolearn") or {}
    if core.get("enabled") is not None:
        _setenv("AUTOLEARN_ENABLED", 1 if core.get("enabled") else 0)
    if core.get("patterns"):
        # minimal switch to embed on/off
        for pat in core["patterns"]:
            if str(pat.get("answer_embed", False)).lower() in ("1","true","yes"):
                _setenv("AUTOLEARN_EMBED","1")
    return {"autolearn_enabled": os.getenv("AUTOLEARN_ENABLED","1"), "embed": os.getenv("AUTOLEARN_EMBED","1")}

def _apply_selfheal_yaml(data: Dict[str, Any]):
    if not isinstance(data, dict): return {}
    core = data.get("selfheal") or {}
    if core.get("approvals_required") is not None:
        _setenv("SELFHEAL_APPROVALS", 0 if core.get("approvals_required") is False else 1)
    gh = core.get("github") or {}
    if gh.get("push_enabled") is not None:
        _setenv("SELFHEAL_USE_GIT", 1 if gh.get("push_enabled") else 0)
    if gh.get("repo"): _setenv("GITHUB_REPO", gh["repo"])
    if gh.get("branch"): _setenv("GITHUB_BRANCH", gh["branch"])
    # restart mode mapping
    rst = core.get("restart") or {}
    if rst.get("mode"): _setenv("SELFHEAL_RESTART_MODE", rst["mode"])
    return {"approvals": os.getenv("SELFHEAL_APPROVALS","0"), "git": os.getenv("SELFHEAL_USE_GIT","0")}

class ConfigHotReload(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._task = None
        self._mtimes = {}

    async def _loop(self):
        if not ENABLED:
            log.info("[hotreload] disabled via CONFIG_WATCH=0")
            return
        await asyncio.sleep(1.0)
        log.info("[hotreload] watching %s (every %.1fs)", CONFIG_DIR, POLL_SEC)
        while True:
            try:
                changed = []
                ai = CONFIG_DIR / "ai.yaml"
                autolearn = CONFIG_DIR / "autolearn.yaml"
                selfheal = CONFIG_DIR / "selfheal.yaml"
                persona = CONFIG_DIR / "persona.md"
                for p in (ai, autolearn, selfheal, persona):
                    m = _mtime(p)
                    if m and self._mtimes.get(p) != m:
                        self._mtimes[p] = m
                        changed.append(p)
                for p in changed:
                    payload = {}
                    if p.name == "ai.yaml":
                        data = _load_yaml(p); payload = {"ai": _apply_ai_yaml(data)}
                    elif p.name == "autolearn.yaml":
                        data = _load_yaml(p); payload = {"autolearn": _apply_autolearn_yaml(data)}
                    elif p.name == "selfheal.yaml":
                        data = _load_yaml(p); payload = {"selfheal": _apply_selfheal_yaml(data)}
                    elif p.name == "persona.md":
                        _setenv("PERSONA_FILE", str(p)); payload = {"persona": {"file": str(p)}}
                    log.info("[hotreload] reloaded %s -> %s", p.name, payload)
                    try:
                        self.bot.dispatch("config_reloaded", p.name, payload)
                    except Exception as e:
                        log.info("[hotreload] dispatch failed: %r", e)
            except Exception as e:
                log.info("[hotreload] loop err: %r", e)
            await asyncio.sleep(POLL_SEC)

    @commands.Cog.listener()
    async def on_ready(self):
        if self._task is None:
            self._task = asyncio.create_task(self._loop())
async def setup(bot):
    try:
        await bot.add_cog(ConfigHotReload(bot))
    except Exception as e:
        log.info("[hotreload] setup swallowed: %r", e)