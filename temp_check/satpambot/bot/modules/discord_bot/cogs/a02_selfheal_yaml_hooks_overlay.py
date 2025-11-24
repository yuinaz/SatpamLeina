
# a02_selfheal_yaml_hooks_overlay.py (v7.8)
# Parse satpambot/config/selfheal.yaml with detailed watchers/rules
from discord.ext import commands
import os, logging, re
from pathlib import Path
from typing import List, Dict, Any

log = logging.getLogger(__name__)
CFG_DIR = Path(os.getenv("CONFIG_DIR", "satpambot/config"))
CFG_PATH = CFG_DIR / "selfheal.yaml"

def _safe_yaml_load(p: Path):
    try:
        import yaml
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        log.info("[selfheal-hooks] no selfheal.yaml at %s", p)
    except Exception as e:
        log.info("[selfheal-hooks] yaml error: %r", e)
    return None

def _compile_watchers(data: Dict[str, Any]):
    out = []
    for w in (data.get("watchers") or []):
        if not isinstance(w, dict):
            continue
        pat = w.get("match") or ""
        try:
            rx = re.compile(pat)
        except Exception as e:
            log.info("[selfheal-hooks] bad watcher regex %r: %r", pat, e)
            rx = None
        out.append({
            "id": w.get("id") or pat[:24],
            "regex": rx,
            "action": (w.get("action") or "patch"),
            "module": w.get("module"),
            "patch": w.get("patch"),
            "restart_on_apply": bool(w.get("restart_on_apply", True)),
        })
    return out

class SelfHealYamlHooks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _parse(self):
        data = _safe_yaml_load(CFG_PATH) or {}
        core = data.get("selfheal") or {}
        cfg = {
            "approvals_required": bool(core.get("approvals_required", False)),
            "use_git": bool((core.get("github") or {}).get("push_enabled", False)),
            "repo": (core.get("github") or {}).get("repo"),
            "branch": (core.get("github") or {}).get("branch") or "main",
            "restart_mode": (core.get("restart") or {}).get("mode") or "graceful",
            "watchers": _compile_watchers(core),
        }
        return cfg

    def _match_selfheal(self, name, cog):
        n = (name or "").lower()
        if "selfheal" in n or "autoexec" in n or "autofix" in n: return True
        return any(hasattr(cog, k) for k in ("selfheal", "restart_mode", "approvals_required"))

    async def _apply_cfg(self, cog, cfg):
        changed = False
        # Prefer explicit hooks
        for hook in ("on_config_changed", "set_rules", "set_watchers", "reload_from_yaml", "reload_from_env"):
            fn = getattr(cog, hook, None)
            if callable(fn):
                try:
                    if hook == "on_config_changed":
                        res = fn("selfheal", cfg)
                    elif hook in ("set_rules","set_watchers"):
                        res = fn(cfg["watchers"])
                    else:
                        res = fn()
                    if hasattr(res, "__await__"):
                        await res
                    changed = True
                    break
                except Exception as e:
                    log.info("[selfheal-hooks] %s.%s fail: %r", cog.__class__.__name__, hook, e)
        # Fallback: assign attributes
        try:
            for k in ("approvals_required","restart_mode"):
                if hasattr(cog, k):
                    setattr(cog, k, cfg[k]); changed = True
            for k_attr, k_cfg in (("use_git","use_git"), ("github_repo","repo"), ("github_branch","branch")):
                if hasattr(cog, k_attr) and cfg.get(k_cfg) is not None:
                    setattr(cog, k_attr, cfg[k_cfg]); changed = True
            if hasattr(cog, "watchers") and cfg.get("watchers") is not None:
                setattr(cog, "watchers", cfg["watchers"]); changed = True
        except Exception as e:
            log.info("[selfheal-hooks] assign fail: %r", e)
        return changed

    @commands.Cog.listener()
    async def on_config_reloaded(self, name, payload):
        if name not in ("selfheal.yaml",):
            return
        cfg = self._parse()
        applied = 0
        for cname, cog in list(self.bot.cogs.items()):
            try:
                if self._match_selfheal(cname, cog):
                    ok = await self._apply_cfg(cog, cfg)
                    if ok: applied += 1
            except Exception:
                pass
        log.info("[selfheal-hooks] applied=%s restart=%s approvals=%s watchers=%s",
                 applied, cfg.get("restart_mode"), cfg.get("approvals_required"), len(cfg.get("watchers") or []))

    @commands.Cog.listener()
    async def on_ready(self):
        if CFG_PATH.exists():
            await self.on_config_reloaded("selfheal.yaml", {"selfheal":"boot"})
async def setup(bot):
    await bot.add_cog(SelfHealYamlHooks(bot))