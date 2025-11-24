from __future__ import annotations
import os, json, glob, logging
from pathlib import Path
from typing import Dict, Any, Optional
from discord.ext import commands

log = logging.getLogger(__name__)

BASES = [
    Path("data/config/overrides.json"),
    Path("data/config/overrides.render-free.json"),
]
PATCH_GLOB = "data/config/overrides.*.patch.json"

def _load_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("[env_overrides] read %s failed: %r", p, e)
    return None

def _apply_env(d: Dict[str, Any]) -> int:
    """Accepts either {'env': {...}} or flat {...}; writes to os.environ (strings only)."""
    if not isinstance(d, dict): return 0
    envmap = d.get("env", d)
    cnt = 0
    for k, v in envmap.items():
        try:
            if isinstance(v, (dict, list)):
                v = json.dumps(v, ensure_ascii=False)
            os.environ[str(k)] = str(v)
            cnt += 1
        except Exception as e:
            log.warning("[env_overrides] skip %s: %r", k, e)
    return cnt

class EnvOverridesLoaderOverlay(commands.Cog):
    """Loads overrides JSON files into process ENV. No side effects at import; runs on_ready once."""
    def __init__(self, bot):
        self.bot = bot
        self._done = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._done:
            return
        total = 0
        # Base files in order
        for p in BASES:
            d = _load_json(p)
            if d:
                total += _apply_env(d)
                log.info("[env_overrides] applied %s", p)
        # Patch files (merge last, override previous)
        for pf in sorted(glob.glob(PATCH_GLOB)):
            try:
                d = _load_json(Path(pf))
                if d:
                    total += _apply_env(d)
                    log.info("[env_overrides] merged %s", pf)
            except Exception as e:
                log.warning("[env_overrides] skip patch %s: %r", pf, e)
        self._done = True
        log.info("[env_overrides] done: %s entries", total)

async def setup(bot: commands.Bot):
    await bot.add_cog(EnvOverridesLoaderOverlay(bot))
    log.info("[env_overrides] loader ready")
