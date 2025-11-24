
from __future__ import annotations
import logging, asyncio
from discord.ext import commands

log = logging.getLogger(__name__)

class PreferUpstashTimeoutGuard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._patched = False
        self._patch()

    def _patch(self):
        try:
            from satpambot.bot.modules.discord_bot.cogs import a00_prefer_upstash_bootstrap as base
        except Exception as e:
            log.debug("[upstash-guard] base import failed: %r", e)
            return
        try:
            import httpx
            if hasattr(base, "_upstash_get"):
                _orig_get = base._upstash_get
                async def _safe_get(client, key):
                    try:
                        if hasattr(client, "timeout"):
                            client.timeout = httpx.Timeout(2.5, read=2.5, write=2.5, pool=2.5)
                    except Exception:
                        pass
                    try:
                        return await _orig_get(client, key)
                    except Exception as e:
                        raise RuntimeError("UPSTASH_TIMEOUT") from e
                base._upstash_get = _safe_get  # type: ignore
        except Exception as e:
            log.debug("[upstash-guard] patch _upstash_get failed: %r", e)

        try:
            _orig_ready = base.PreferUpstashBootstrap.on_ready_do
            async def _safe_ready(self, *a, **k):
                try:
                    return await _orig_ready(self, *a, **k)
                except Exception as e:
                    log.warning("[prefer-upstash] bootstrap skipped due to: %r", e)
                    try:
                        from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
                        kv = PinnedJSONKV(self.bot)
                        m = await kv.get_map()
                        label = str(m.get("xp:stage:label") or "")
                        if label.startswith(("KULIAH-","MAGANG")):
                            cur   = int(m.get("xp:stage:current", 0) or 0)
                            req   = int(m.get("xp:stage:required", 1) or 1)
                            pct   = float(m.get("xp:stage:percent", 0) or 0.0)
                            status = f"{label} ({pct}%)"
                            import json
                            st_json = json.dumps({
                                "label": label, "percent": pct, "remaining": max(0, req-cur),
                                "senior_total": int(m.get("xp:bot:senior_total", 0) or 0),
                                "stage": {"start_total": max(0, int(m.get("xp:bot:senior_total", 0) or 0) - cur),
                                          "required": req, "current": cur}
                            }, separators=(",",":"))
                            await kv.set_multi({"learning:status": status, "learning:status_json": st_json})
                            log.info("[prefer-upstash] fallback wrote learning status from pinned stage")
                    except Exception as ee:
                        log.debug("[prefer-upstash] fallback failed: %r", ee)
                    return
            base.PreferUpstashBootstrap.on_ready_do = _safe_ready  # type: ignore
        except Exception as e:
            log.debug("[upstash-guard] patch on_ready_do failed: %r", e)

        self._patched = True
        log.info("[upstash-guard] prefer_upstash bootstrap patched (timeouts + safe fallback).")

    @commands.Cog.listener()
    async def on_ready(self):
        pass

async def setup(bot):
    await bot.add_cog(PreferUpstashTimeoutGuard(bot))
