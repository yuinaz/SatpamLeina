from __future__ import annotations

from discord.ext import commands

import logging

log = logging.getLogger(__name__)

TARGET_EXT = "satpambot.bot.modules.discord_bot.cogs.auto_update_manager"

class DisableAutoUpdate(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        log.info("[disable-talking] active; removed=[] blocked_prefixes=[]")
async def setup(bot: commands.Bot):
    # discord.py v2 uses async load/unload
    try:
        await bot.unload_extension(TARGET_EXT)  # if loaded by default
    except Exception:
        pass
    await bot.add_cog(DisableAutoUpdate(bot))