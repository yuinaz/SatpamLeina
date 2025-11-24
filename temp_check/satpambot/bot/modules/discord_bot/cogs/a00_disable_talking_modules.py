
# a00_disable_talking_modules.py

from discord.ext import commands
import logging
log = logging.getLogger(__name__)
BLOCK_PREFIXES = [
    "satpambot.bot.modules.discord_bot.cogs.chat_neurolite",
    "satpambot.bot.modules.discord_bot.cogs.public_send_router",
    "satpambot.bot.modules.discord_bot.cogs.slash_list_broadcast",
    "satpambot.bot.modules.discord_bot.cogs.diag_public",
]
def _is_blocked(name: str) -> bool:
    for p in BLOCK_PREFIXES:
        if name.startswith(p): return True
    return False
class DisableTalking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._orig_load_ext = None
    async def cog_load(self):
        removed = []
        for name in list(self.bot.extensions.keys()):
            if _is_blocked(name):
                try:
                    self.bot.unload_extension(name); removed.append(name)
                except Exception as e:
                    log.warning("[disable-talking] unload fail %s: %s", name, e)
        self._orig_load_ext = self.bot.load_extension
        def _guarded_load_ext(modname: str, *a, **kw):
            if _is_blocked(modname):
                log.info("[disable-talking] suppress load: %s", modname); return
            return self._orig_load_ext(modname, *a, **kw)
        self.bot.load_extension = _guarded_load_ext
        log.info("[disable-talking] active; removed=%s blocked_prefixes=%s", removed, BLOCK_PREFIXES)
    def cog_unload(self):
        try:
            if self._orig_load_ext: self.bot.load_extension = self._orig_load_ext
        except Exception: pass
async def setup(bot: commands.Bot):
    await bot.add_cog(DisableTalking(bot))