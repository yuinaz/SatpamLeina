from __future__ import annotations

from discord.ext import commands

import os, logging

from ..helpers import env_store

log = logging.getLogger(__name__)

class EnvBootstrap(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        allow_all = (env_store.get("ENVSTORE_ALLOW_ALL") or os.getenv("ENVSTORE_ALLOW_ALL") or "0") == "1"
        overwrite_db = (env_store.get("ENVSTORE_OVERWRITE_DB") or os.getenv("ENVSTORE_OVERWRITE_DB") or "0") == "1"
        # Import semua ENV process ke DB (sekali boot, optional)
        if allow_all:
            for k, v in os.environ.items():
                if not overwrite_db:
                    if env_store.get(k) is not None:
                        continue
                try:
                    env_store.set(k, v, source="import-all")
                except Exception:
                    pass
async def setup(bot):
    await bot.add_cog(EnvBootstrap(bot))