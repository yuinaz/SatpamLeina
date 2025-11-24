from __future__ import annotations

from discord.ext import commands
import logging

from discord.ext import tasks
from satpambot.config.auto_local_sync import unify_env_and_json_to_local, RESCAN_INTERVAL_SEC

log = logging.getLogger(__name__)

class AutoLocalSync(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        try:
            path, data, removed = unify_env_and_json_to_local()
            log.info("[auto_local_sync] local.json updated at %s (keys=%d, removed=%d)",
                     path, len(data.keys()), len(removed))
            if RESCAN_INTERVAL_SEC and RESCAN_INTERVAL_SEC > 0:
                self._loop.start()
        except Exception as e:
            log.error("[auto_local_sync] failed: %s", e)

    def cog_unload(self):
        try:
            if getattr(self, "_loop", None):
                self._loop.cancel()
        except Exception:
            pass

    @tasks.loop(seconds=RESCAN_INTERVAL_SEC or 3600)
    async def _loop(self):
        try:
            path, data, removed = unify_env_and_json_to_local()
            log.info("[auto_local_sync] periodic refresh local.json (keys=%d)", len(data.keys()))
        except Exception as e:
            log.warning("[auto_local_sync] periodic refresh failed: %s", e)
async def setup(bot: commands.Bot):
    await bot.add_cog(AutoLocalSync(bot))