
"""
a21_curriculum_autoload_guard_kv_overlay.py
- Disable TK autoload based on Upstash KV (no Render ENV needed).
- If cfg:curriculum:pref == "senior" OR learning:status startswith "KULIAH" OR learning:phase has "senior",
  we patch CurriculumAutoload.on_ready -> no-op and try to unload TK modules already loaded.
"""

from __future__ import annotations
import os, logging, importlib, asyncio
from typing import Optional
from discord.ext import commands

log = logging.getLogger(__name__)

def _pick(k: str) -> Optional[str]:
    v = os.getenv(k)
    if v: return v
    # compat names
    if k == "UPSTASH_REST_URL":
        return os.getenv("UPSTASH_REDIS_REST_URL")
    if k == "UPSTASH_REST_TOKEN":
        return os.getenv("UPSTASH_REDIS_REST_TOKEN")
    return None

async def _kv_get(path: str) -> Optional[str]:
    url = _pick("UPSTASH_REST_URL")
    tok = _pick("UPSTASH_REST_TOKEN")
    if not (url and tok):
        return None
    try:
        import httpx
    except Exception:
        return None
    try:
        async with httpx.AsyncClient(timeout=5) as cli:
            r = await cli.get(f"{url}/{path}", headers={"Authorization": f"Bearer {tok}"})
            j = r.json()
            return j.get("result")
    except Exception as e:  # pragma: no cover
        log.debug("[kv-guard] kv get fail: %r", e)
        return None

async def _prefer_senior_by_kv() -> bool:
    pref = await _kv_get("get/cfg:curriculum:pref")
    if pref and str(pref).lower() == "tk":
        return False
    if pref and str(pref).lower() == "senior":
        return True
    # If not set, default to senior; but still inspect learning keys for hints
    st = await _kv_get("get/learning:status") or ""
    if str(st).upper().startswith("KULIAH"):
        return True
    ph = await _kv_get("get/learning:phase") or ""
    if "senior" in str(ph).lower():
        return True
    return True  # default senior

async def _unload_if_loaded(bot, ext: str):
    try:
        if ext in bot.extensions:
            await bot.unload_extension(ext)  # type: ignore
            log.info("[curriculum_guard_kv] unloaded %s", ext)
    except Exception as e:
        log.debug("[curriculum_guard_kv] unload %s fail: %r", ext, e)

class CurriculumAutoloadGuardKV(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Run after bot is ready-ish
        asyncio.create_task(self._apply())

    async def _apply(self):
        try:
            prefer_senior = await _prefer_senior_by_kv()
            if not prefer_senior:
                log.info("[curriculum_guard_kv] prefer_senior=False -> no guard")
                return
            # Patch autoload on_ready to noop
            try:
                m = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a21_curriculum_autoload")
                if hasattr(m, "CurriculumAutoload"):
                    def _noop(*a, **k): pass
                    setattr(m.CurriculumAutoload, "on_ready", _noop)  # type: ignore[attr-defined]
                    log.info("[curriculum_guard_kv] patched CurriculumAutoload.on_ready -> noop")
            except Exception as e:
                log.debug("[curriculum_guard_kv] patch skip: %r", e)
            # Also unload TK modules if already loaded
            await _unload_if_loaded(self.bot, "satpambot.bot.modules.discord_bot.cogs.a20_curriculum_tk_sd")
            await _unload_if_loaded(self.bot, "satpambot.bot.modules.discord_bot.cogs.a22_tk_xp_overlay")
        except Exception as e:
            log.debug("[curriculum_guard_kv] apply error: %r", e)

async def setup(bot):
    await bot.add_cog(CurriculumAutoloadGuardKV(bot))
