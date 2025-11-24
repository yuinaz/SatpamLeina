
# a00_quiet_shadow_public_silencer.py

from discord.ext import commands
import logging
TARGET_LOGGER = "satpambot.bot.modules.discord_bot.cogs.shadow_public_silencer"
class QuietSilencer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._logger = logging.getLogger(TARGET_LOGGER)
        self._prev_level = self._logger.level
        self._logger.setLevel(logging.ERROR)
        for h in self._logger.handlers:
            try: h.setLevel(logging.ERROR)
            except Exception: pass
        logging.getLogger(__name__).info("[quiet-silencer] logger '%s' set to ERROR", TARGET_LOGGER)
    def cog_unload(self):
        try: self._logger.setLevel(self._prev_level)
        except Exception: pass
async def setup(bot):
    await bot.add_cog(QuietSilencer(bot))