
# a02_autolearn_yaml_hooks_overlay.py (v7.8)
# Parse satpambot/config/autolearn.yaml in detail (regex, channels, memory)
from discord.ext import commands
import os, logging, types, re
from pathlib import Path
from typing import List, Dict, Any

log = logging.getLogger(__name__)
CFG_DIR = Path(os.getenv("CONFIG_DIR", "satpambot/config"))
CFG_PATH = CFG_DIR / "autolearn.yaml"

def _safe_yaml_load(p: Path):
    try:
        import yaml
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        log.info("[autolearn-hooks] no autolearn.yaml found at %s", p)
    except Exception as e:
        log.info("[autolearn-hooks] yaml error: %r", e)
    return None

_FLAG_MAP = {
    "I": re.IGNORECASE, "IGNORECASE": re.IGNORECASE,
    "M": re.MULTILINE,  "MULTILINE": re.MULTILINE,
    "S": re.DOTALL,     "DOTALL": re.DOTALL,
    "U": re.UNICODE,    "UNICODE": re.UNICODE,
}

def _compile_regex(spec: Dict[str, Any]):
    pat = spec.get("regex") or ""
    flags = 0
    for fl in (spec.get("flags") or []):
        fl = str(fl).strip().upper()
        if fl in _FLAG_MAP: flags |= _FLAG_MAP[fl]
    try:
        return re.compile(pat, flags)
    except Exception as e:
        log.info("[autolearn-hooks] bad regex %r: %r", pat, e)
        return None

def _coerce_channel_id(x):
    # accept raw int id or "#name" as plain string (we just store string for filter cogs to resolve)
    if isinstance(x, int): return x
    s = str(x).strip()
    try:
        return int(s)
    except:
        return s

class AutoLearnYamlHooks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _parse(self):
        data = _safe_yaml_load(CFG_PATH) or {}
        core = data.get("autolearn") or {}
        enabled = bool(core.get("enabled", True))
        watch = [_coerce_channel_id(x) for x in (core.get("watch_channels") or [])]
        patterns = []
        for spec in (core.get("patterns") or []):
            rx = _compile_regex(spec) if isinstance(spec, dict) else None
            if not rx: 
                continue
            patterns.append({
                "name": spec.get("name") or spec.get("type") or "generic",
                "regex": rx,
                "answer_embed": bool(spec.get("answer_embed", True)),
                "summarize": bool(spec.get("summarize", False)),
            })
        mem = core.get("memory") or {}
        memory_cfg = {
            "window": int(mem.get("window", 30)),
            "cap": int(mem.get("cap", 50)),
            "min_delta": int(mem.get("min_delta", 12)),
            "xp_award": {
                "per_item": int((mem.get("xp_award") or {}).get("per_item", 1)),
                "burst_factor": float((mem.get("xp_award") or {}).get("burst_factor", 1.5)),
                "cooldown_sec": int((mem.get("xp_award") or {}).get("cooldown_sec", 600)),
            }
        }
        snapshot = {
            "enabled": enabled,
            "watch_channels": watch,
            "patterns": patterns,
            "memory": memory_cfg,
        }
        return snapshot

    def _match_autolearn(self, name, cog):
        n = (name or "").lower()
        if "autolearn" in n or "qna" in n: return True
        # marker heuristics
        return any(hasattr(cog, k) for k in ("autolearn", "answer_embed", "embed_enabled", "qa_regex", "patterns"))

    async def _apply_snapshot(self, cog, snap):
        # Try known hooks, then set attributes.
        changed = False
        # Known hooks
        for hook in ("on_config_changed", "set_patterns", "reload_from_yaml", "reload_from_env"):
            fn = getattr(cog, hook, None)
            if callable(fn):
                try:
                    if hook == "on_config_changed":
                        res = fn("autolearn", snap)
                    elif hook == "set_patterns":
                        res = fn(snap.get("patterns", []), snap.get("watch_channels", []))
                    else:
                        res = fn()
                    if hasattr(res, "__await__"):
                        await res
                    changed = True
                    break
                except Exception as e:
                    log.info("[autolearn-hooks] %s.%s fail: %r", cog.__class__.__name__, hook, e)
        # Fallback direct assignment
        try:
            if hasattr(cog, "enabled"): setattr(cog, "enabled", snap["enabled"]); changed = True
            if hasattr(cog, "answer_embed"): setattr(cog, "answer_embed", any(p["answer_embed"] for p in snap["patterns"]) if snap["patterns"] else True); changed = True
            if hasattr(cog, "patterns"): setattr(cog, "patterns", snap["patterns"]); changed = True
            if hasattr(cog, "qa_regex"):
                # pick first qa-like regex
                qa = next((p for p in snap["patterns"] if p["name"] in ("qa","qna","question","qa_main")), None)
                if qa: setattr(cog, "qa_regex", qa["regex"]); changed = True
            # memory tuning
            for k in ("memory_window","memory_cap","memory_min_delta"):
                if hasattr(cog, k):
                    # map keys
                    val = snap["memory"]["window"] if k=="memory_window" else snap["memory"]["cap"] if k=="memory_cap" else snap["memory"]["min_delta"]
                    setattr(cog, k, val); changed = True
        except Exception as e:
            log.info("[autolearn-hooks] assign fail: %r", e)
        return changed

    @commands.Cog.listener()
    async def on_config_reloaded(self, name, payload):
        if name not in ("autolearn.yaml",):
            return
        snap = self._parse()
        applied = 0
        for cname, cog in list(self.bot.cogs.items()):
            try:
                if self._match_autolearn(cname, cog):
                    ok = await self._apply_snapshot(cog, snap)
                    if ok: applied += 1
            except Exception:
                pass
        log.info("[autolearn-hooks] applied=%s cfg=%s", applied, {k:v for k,v in snap.items() if k!="patterns"})

    @commands.Cog.listener()
    async def on_ready(self):
        # initial load if file exists
        if CFG_PATH.exists():
            await self.on_config_reloaded("autolearn.yaml", {"autolearn":"boot"})
async def setup(bot):
    await bot.add_cog(AutoLearnYamlHooks(bot))