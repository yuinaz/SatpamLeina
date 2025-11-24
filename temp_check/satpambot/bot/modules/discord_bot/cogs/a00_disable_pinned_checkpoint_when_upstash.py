
# a00_disable_pinned_checkpoint_when_upstash.py
# When Upstash is configured, unload the pinned-checkpoint backend so boot always prefers Upstash.
from discord.ext import commands
import os

try:
    from satpambot.config.runtime import cfg
    def _cfg(k, default=None):
        try:
            v = cfg(k)
            return default if v in (None, "") else v
        except Exception:
            return os.getenv(k, default)
except Exception:
    def _cfg(k, default=None):
        return os.getenv(k, default)

class DisablePinnedCheckpoint(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        url   = _cfg("UPSTASH_REDIS_REST_URL")
        token = _cfg("UPSTASH_REDIS_REST_TOKEN")
        if not (url and token):
            return
        # Attempt to unload extension that restores XP from pinned messages
        for name in list(self.bot.extensions.keys()):
            if name.endswith(".a01_xp_checkpoint_discord_backend"):
                try:
                    await self.bot.unload_extension(name)
                except Exception:
                    pass
async def setup(bot):
    await bot.add_cog(DisablePinnedCheckpoint(bot))