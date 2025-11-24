
from __future__ import annotations
import json, logging
from discord.ext import commands

log = logging.getLogger(__name__)

class PreferUpstashBootstrapForceKuliah(commands.Cog):
    """Monkey-patch prefer_upstash bootstrap to FORCE learning:status(_json) to KULIAH/MAGANG from pinned stage."""
    def __init__(self, bot):
        self.bot = bot
        self._patch()

    def _patch(self):
        try:
            from satpambot.bot.modules.discord_bot.cogs import a00_prefer_upstash_bootstrap as base
        except Exception as e:
            log.debug("[force-kuliah-bootstrap] base import failed: %r", e); return

        # wrap fetch to sanitize status/status_json
        try:
            _orig = base._fetch_state_from_upstash
            async def _wrap_fetch(*a, **k):
                s = await _orig(*a, **k)
                try:
                    # Prefer pinned stage (most reliable)
                    from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
                    kv = PinnedJSONKV(self.bot)
                    m = await kv.get_map()
                    label = str(m.get("xp:stage:label") or "")
                    cur   = int(m.get("xp:stage:current", 0) or 0)
                    req   = int(m.get("xp:stage:required", 1) or 1)
                    pct   = float(m.get("xp:stage:percent", 0) or 0.0)
                    total = int(m.get("xp:bot:senior_total", 0) or 0)
                    if label.startswith(("KULIAH-","MAGANG")):
                        s["status"] = f"{label} ({pct}%)"
                        s["status_json"] = json.dumps({
                            "label": label, "percent": pct, "remaining": max(0, req-cur),
                            "senior_total": total,
                            "stage": {"start_total": max(0, total - cur), "required": req, "current": cur}
                        }, separators=(",",":"))
                except Exception as e:
                    log.debug("[force-kuliah-bootstrap] sanitize failed: %r", e)
                return s
            base._fetch_state_from_upstash = _wrap_fetch  # type: ignore
            log.info("[force-kuliah-bootstrap] patched _fetch_state_from_upstash to force KULIAH status.")
        except Exception as e:
            log.debug("[force-kuliah-bootstrap] patch fetch failed: %r", e)

    @commands.Cog.listener()
    async def on_ready(self):
        pass

async def setup(bot):
    await bot.add_cog(PreferUpstashBootstrapForceKuliah(bot))
