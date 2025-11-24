from discord.ext import commands
import os, json, logging
from pathlib import Path

log = logging.getLogger(__name__)

LOCAL_JSON_PATHS = [
    Path("satpambot_config.local.json"),
    Path("satpambot/config/local.json"),
    Path("satpambot/bot/config/local.json"),
    Path("local.json"),
]

def _load_local():
    for p in LOCAL_JSON_PATHS:
        try:
            if p.exists():
                return json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning("[upstash_runtime] failed to read %s: %r", p, e)
    return {}

class UpstashRuntimeOverlay(commands.Cog):
    """Ensure XP Store uses Upstash even on Render free plan.
    This overlay reads UPSTASH creds from local json if present and sets envs
    before xp_core_store_bridge initializes.
    """
    def __init__(self, bot):
        self.bot = bot
        cfg = _load_local()
        url = cfg.get("UPSTASH_REST_URL") or cfg.get("upstash_rest_url") or os.environ.get("UPSTASH_REST_URL")
        token = cfg.get("UPSTASH_REST_TOKEN") or cfg.get("upstash_rest_token") or os.environ.get("UPSTASH_REST_TOKEN")

        # Force-enable Upstash; xp_core_store_bridge will read these
        os.environ.setdefault("UPSTASH_ENABLE", "1")

        if url and token:
            os.environ.setdefault("UPSTASH_REST_URL", str(url))
            os.environ.setdefault("UPSTASH_REST_TOKEN", str(token))
            log.info("[upstash_runtime] enabled (url+token loaded from local.json/env)")
        else:
            log.warning("[upstash_runtime] UPSTASH_REST_URL/TOKEN missing; enable flag set, bridge will log if it cannot connect.")

    async def cog_load(self):
        return
async def setup(bot):
    await bot.add_cog(UpstashRuntimeOverlay(bot))