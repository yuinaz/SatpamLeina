
from discord.ext import commands
class PersonaOverlayGuardPatch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Provide safe fallback to avoid AttributeError
        if not hasattr(bot, "get_active_persona"):
            async def _get_active_persona(_ctx=None):
                return "default"
            bot.get_active_persona = _get_active_persona
async def setup(bot):
    await bot.add_cog(PersonaOverlayGuardPatch(bot))