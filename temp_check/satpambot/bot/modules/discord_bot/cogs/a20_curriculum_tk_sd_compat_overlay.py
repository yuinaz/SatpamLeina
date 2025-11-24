
"""
a20_curriculum_tk_sd_compat_overlay.py
- Adds missing attributes to a20_curriculum_tk_sd used by TK XP overlays:
  * PROGRESS_FILE  (env TK_PROGRESS_FILE or default data/neuro-lite/learn_progress_tk.json)
  * _probe_total_xp_runtime(bot) -> int (reads XP_TK_KEY from Upstash, default xp:bot:tk_total)
"""
import os, logging, importlib
from typing import Optional
from discord.ext import commands
log = logging.getLogger(__name__)

def _env_pick(k: str) -> Optional[str]:
    v = os.getenv(k)
    if v: return v
    if k == "UPSTASH_REST_URL":
        return os.getenv("UPSTASH_REDIS_REST_URL")
    if k == "UPSTASH_REST_TOKEN":
        return os.getenv("UPSTASH_REDIS_REST_TOKEN")
    return None

async def _upstash_get(path: str):
    try:
        import httpx
    except Exception as e:
        log.warning("[tk-compat] httpx missing; cannot probe TK total (%s)", e)
        return None
    url = _env_pick("UPSTASH_REST_URL")
    tok = _env_pick("UPSTASH_REST_TOKEN")
    if not (url and tok):
        log.warning("[tk-compat] Upstash env missing; cannot probe TK total")
        return None
    try:
        async with httpx.AsyncClient(timeout=6) as cli:
            r = await cli.get(f"{url}/{path}", headers={"Authorization": f"Bearer {tok}"})
            if r.status_code // 100 != 2:
                return None
            j = r.json()
            return j.get("result")
    except Exception as e:
        log.warning("[tk-compat] Upstash GET failed: %s", e)
        return None

class TKCurriculumCompatOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._patch_module()
    def _patch_module(self):
        try:
            m = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a20_curriculum_tk_sd")
        except Exception as e:
            log.warning("[tk-compat] cannot import a20_curriculum_tk_sd: %s", e)
            return
        if not hasattr(m, "PROGRESS_FILE"):
            pf = os.getenv("TK_PROGRESS_FILE", "data/neuro-lite/learn_progress_tk.json")
            setattr(m, "PROGRESS_FILE", pf)
            log.info("[tk-compat] set PROGRESS_FILE=%s", pf)
        if not hasattr(m, "_probe_total_xp_runtime"):
            async def _probe_total_xp_runtime(bot):
                key = os.getenv("XP_TK_KEY", "xp:bot:tk_total")
                v = await _upstash_get(f"get/{key}")
                try:
                    return int(str(v))
                except Exception:
                    return 0
            setattr(m, "_probe_total_xp_runtime", _probe_total_xp_runtime)
            log.info("[tk-compat] installed _probe_total_xp_runtime()")

async def setup(bot):
    await bot.add_cog(TKCurriculumCompatOverlay(bot))
