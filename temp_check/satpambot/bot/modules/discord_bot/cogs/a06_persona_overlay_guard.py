
# a06_persona_overlay_guard.py
from discord.ext import commands
import logging

log = logging.getLogger(__name__)

class PersonaOverlayGuard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        try:
            from satpambot.bot.modules.discord_bot.cogs.personality_governor import PersonaOverlay
        except Exception as e:
            log.debug("[persona-guard] personality_governor not available: %r", e)
            return
        if not hasattr(PersonaOverlay, "get_active_persona"):
            def get_active_persona(self, *a, **kw):
                # default persona name; keep behavior stable without changing config
                return "Leina"
            PersonaOverlay.get_active_persona = get_active_persona
            log.info("[persona-guard] injected PersonaOverlay.get_active_persona()")
        else:
            log.debug("[persona-guard] PersonaOverlay already has get_active_persona")
async def setup(bot):
    await bot.add_cog(PersonaOverlayGuard(bot))