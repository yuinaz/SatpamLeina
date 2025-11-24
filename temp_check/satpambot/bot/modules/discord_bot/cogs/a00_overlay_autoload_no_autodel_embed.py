from __future__ import annotations

from discord.ext import commands

import logging
log = logging.getLogger(__name__)
MODULES = [
    "satpambot.bot.modules.discord_bot.cogs.a05_autodelete_exempt_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a06_status_embed_helper",
    "satpambot.bot.modules.discord_bot.cogs.a06_selfheal_embed_overlay",
]
class SatpamAutoloadNoAutoDelEmbed(commands.Cog):
    def __init__(self, bot): self.bot = bot
    async def cog_load(self):
        for m in MODULES:
            try:
                await self.bot.load_extension(m) if m.endswith("_overlay") else __import__(m)
                # Note: helper module is a normal module (no setup), overlays have setup
                # So we try load_extension for overlays, import for helpers.
                pass
            except Exception as e:
                log.warning("[autoload_no_autodel_embed] %s", e)
async def setup(bot): await bot.add_cog(SatpamAutoloadNoAutoDelEmbed(bot))