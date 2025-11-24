
# a00_persona_overlay_guard_early.py
from discord.ext import commands
import logging

log = logging.getLogger(__name__)

CANDIDATES = [
    "satpambot.bot.modules.discord_bot.cogs.personality_governor",
    "modules.discord_bot.cogs.personality_governor",
    "satpambot.bot.modules.discord_bot.cogs.personality_governor_fix",
]

def _inject():
    for modname in CANDIDATES:
        try:
            m = __import__(modname, fromlist=["*"])
        except Exception:
            continue
        PO = getattr(m, "PersonaOverlay", None)
        if PO and not hasattr(PO, "get_active_persona"):
            def get_active_persona(self, *a, **kw):
                # default persona name; do not change config
                return "Leina"
            setattr(PO, "get_active_persona", get_active_persona)
            log.info("[persona-guard-early] injected PersonaOverlay.get_active_persona() on %s", modname)
            return True
    return False

class PersonaOverlayGuardEarly(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    async def cog_load(self):
        _inject()
async def setup(bot):
    await bot.add_cog(PersonaOverlayGuardEarly(bot))