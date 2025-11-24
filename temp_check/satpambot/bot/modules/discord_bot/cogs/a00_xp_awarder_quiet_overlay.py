from discord.ext import commands

import logging, time, importlib

LOG = logging.getLogger(__name__)
_LAST = 0
def _allow_log():
    global _LAST; now=time.time()
    if now-_LAST<600: return False
    _LAST=now; return True
class XPAwarderQuiet(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            m = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.a08_xp_message_awarder_overlay")
            setattr(m, "QUIET_NO_DIRECT_XP_LOG", True)
            if hasattr(m, "log_warning_no_direct"):
                orig = m.log_warning_no_direct
                def wrap():
                    if _allow_log(): orig()
                setattr(m, "log_warning_no_direct", wrap)
        except Exception as e:
            LOG.debug("[xp-awarder-quiet] skip: %r", e)
async def setup(bot): await bot.add_cog(XPAwarderQuiet(bot))