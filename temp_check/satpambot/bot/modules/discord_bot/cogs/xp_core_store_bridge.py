from discord.ext import commands

import os
import logging

log = logging.getLogger(__name__)

TRUTHY = {"1","true","yes","on","enabled"}

def _boolenv(name: str) -> bool:
    v = os.getenv(name, "")
    return v.lower() in TRUTHY

class XPStoreBridge(commands.Cog):
    """Thin facade that chooses File vs Upstash backend at runtime.
    It also exposes a single 'award' method other cogs can call.
    """
    def __init__(self, bot):
        self.bot = bot
        # Consider multiple signals to enable Upstash, including Render's REST vars.
        has_upstash_url = any(os.getenv(k) for k in (
            "UPSTASH_REDIS_REST_URL", "UPSTASH_REST_URL", "UPSTASH_URL"
        ))
        self.use_upstash = has_upstash_url or _boolenv("UPSTASH_ENABLE") or _boolenv("XP_UPSTASH_ENABLED")
        if self.use_upstash and not _boolenv("UPSTASH_ENABLE"):
            # normalize for downstream code that checks this flag
            os.environ["UPSTASH_ENABLE"] = "1"
        log.info("[xp-bridge] backend=%s (url=%s)",
                 "upstash" if self.use_upstash else "file",
                 os.getenv("UPSTASH_REDIS_REST_URL") or os.getenv("UPSTASH_REST_URL") or "-")

    async def award(self, user_id: int, amount: int, *, guild_id: int|None=None, reason: str|None=None,
                    channel_id: int|None=None, message_id: int|None=None):
        """Unified award entry point used by history renderers and on_message overlays."""
        try:
            if guild_id is None and getattr(self.bot, "guilds", None):
                guild = self.bot.guilds[0]
                guild_id = getattr(guild, "id", None)
            if guild_id is None:
                raise RuntimeError("guild_id required")

            # Prefer V1 service (dynamic KV detection); it's lighter and robust in free Render
            from satpambot.bot.modules.discord_bot.services import xp_store as xp_v1
            added = xp_v1.add_xp(guild_id, user_id, int(amount))
            return added
        except Exception as e:
            log.exception("[xp-bridge] award failed: %r", e)
            raise

async def setup(bot):
    await bot.add_cog(XPStoreBridge(bot))